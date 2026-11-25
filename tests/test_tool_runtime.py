"""Real subprocess deadlines; no network, model, or SMTP required."""
import asyncio
import inspect
import sys
import tempfile
import unittest
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import tool_runtime as runtime
import test_agent_memory as memory_tests
from test_agent_memory import NS


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_success(self):
        result = await runtime.run_isolated(
            [sys.executable, '-c', 'import json; print(json.dumps("ok"))'], b'{}', timeout=5)
        self.assertEqual(result, 'ok')

    async def test_process_timeout_and_next_call(self):
        result = await runtime.run_isolated(
            [sys.executable, '-c', 'import time; time.sleep(30)'], b'{}', timeout=.2)
        self.assertIn(runtime.TIMEOUT_MARKER, result)
        await self.test_process_success()

    async def test_process_cancelled(self):
        task = asyncio.create_task(runtime.run_isolated(
            [sys.executable, '-c', 'import time; time.sleep(30)'], b'{}', timeout=20))
        await asyncio.sleep(.2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_timeout_stops_descendant_process(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'should-not-exist'
            child = f'import time; from pathlib import Path; time.sleep(1.5); Path({str(marker)!r}).write_text("alive")'
            parent = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(30)'
            result = await runtime.run_isolated([sys.executable, '-c', parent], b'{}', timeout=.4)
            self.assertIn(runtime.TIMEOUT_MARKER, result)
            await asyncio.sleep(1.6)
            self.assertFalse(marker.exists())

    async def test_wrapper_preserves_schema_and_direct_calls(self):
        registered = []
        mcp = NS(tool=lambda: lambda fn: registered.append(fn))

        def demo(value: str, count: int = 1) -> str:
            return value * count

        original = runtime.isolated_tool(mcp, __file__)(demo)
        self.assertEqual(original('a', 2), 'aa')
        wrapper = registered[0]
        self.assertTrue(inspect.iscoroutinefunction(wrapper))
        self.assertEqual(inspect.signature(wrapper), inspect.signature(demo))
        with patch.object(runtime, 'run_isolated', new=AsyncMock(return_value='result')) as run:
            self.assertEqual(await wrapper(value='b'), 'result')
            self.assertIn('--run-tool', run.await_args.args[0])

    async def test_deadline_keeps_context_in_same_task(self):
        tasks = []

        @asynccontextmanager
        async def context():
            tasks.append(asyncio.current_task())
            try:
                yield
            finally:
                tasks.append(asyncio.current_task())

        async with AsyncExitStack() as stack:
            with self.assertRaises(TimeoutError):
                async with runtime.deadline(.01):
                    await stack.enter_async_context(context())
                    await asyncio.sleep(10)
        self.assertIs(tasks[0], tasks[1])


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture = memory_tests.AgentMemoryTests()
        fixture.setUp()
        for fn, args, kwargs in fixture._cleanups:
            self.addCleanup(fn, *args, **kwargs)
        fixture._cleanups.clear()
        self.agent = fixture.agent
        self.agent.HERE = Path(fixture.tmp.name)
        self.agent.SERVERS = {'mock': NS()}
        self.closed = []
        self.session = NS(initialize=AsyncMock(), list_tools=AsyncMock(return_value=NS(tools=[], nextCursor=None)))

        @asynccontextmanager
        async def transport(*args, **kwargs):
            try:
                yield None, None
            finally:
                self.closed.append('transport')

        @asynccontextmanager
        async def session(*args, **kwargs):
            try:
                yield self.session
            finally:
                self.closed.append('session')

        self.agent.stdio_client = transport
        self.agent.ClientSession = session

    async def test_initialize_timeout_cleans_connection(self):
        self.agent.MCP_CONNECTION_SECONDS = .01
        self.session.initialize.side_effect = lambda: None

        async def blocked():
            await asyncio.sleep(10)

        self.session.initialize.side_effect = blocked
        with self.assertRaises(RuntimeError):
            async with AsyncExitStack() as stack:
                await self.agent.connect(stack)
        self.assertEqual(self.closed, ['session', 'transport'])

    async def test_discovery_timeout_cleans_connection(self):
        self.agent.MCP_DISCOVERY_SECONDS = .01

        async def blocked():
            await asyncio.sleep(10)

        self.session.list_tools.side_effect = blocked
        with self.assertRaises(RuntimeError):
            async with AsyncExitStack() as stack:
                await self.agent.connect(stack)
        self.assertEqual(self.closed, ['session', 'transport'])

    async def test_pagination_and_duplicate_detection(self):
        self.session.list_tools.side_effect = [
            NS(tools=[NS(name='one')], nextCursor='next'),
            NS(tools=[NS(name='two')], nextCursor=None),
        ]
        async with AsyncExitStack() as stack:
            result = await self.agent.connect(stack)
            self.assertEqual(set(result), {'one', 'two'})
        self.session.list_tools.side_effect = None
        self.session.list_tools.return_value = NS(tools=[NS(name='same'), NS(name='same')], nextCursor=None)
        with self.assertRaises(ValueError):
            async with AsyncExitStack() as stack:
                await self.agent.connect(stack)


if __name__ == '__main__':
    unittest.main()
