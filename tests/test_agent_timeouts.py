"""Characterize current timeout behavior using mocked MCP responses."""
import unittest
import asyncio
import test_agent_memory as memory_tests
from test_agent_memory import NS, response


class TimeoutBehaviorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = memory_tests.AgentMemoryTests()
        self.fixture.setUp()
        for function, args, kwargs in self.fixture._cleanups:
            self.addCleanup(function, *args, **kwargs)
        self.fixture._cleanups.clear()

    async def test_parser_timeout_retries_once_then_allows_only_recall(self):
        f = self.fixture
        name = 'run_file_parser_python'
        f.tools[name] = ('my-tools', f.session, NS(name=name, description=name, inputSchema={'type': 'object'}))
        f.results[name] = '오류: 실행 시간이 60초를 초과했습니다.'
        f.sequence = [response(name, {'code': 'slow'}), response(name, {'code': 'still slow'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertIn(name, [t['function']['name'] for t in f.snapshots[1]['tools']])
        self.assertIn('다시 시도', f.content(f.snapshots[1]))
        self.assertEqual([t['function']['name'] for t in f.snapshots[2]['tools']], ['recall_tool_result'])
        self.assertIn('R1', f.content(f.snapshots[2]))
        self.assertEqual(f.session.call_tool.await_args.kwargs['read_timeout_seconds'].total_seconds(), 130)

    async def test_math_timeout_retries_once_then_allows_only_recall(self):
        f = self.fixture
        f.results['run_math_python'] = '오류: 실행 시간이 30초를 초과했습니다.'
        f.sequence = [response('run_math_python', {'code': 'slow'}),
                      response('run_math_python', {'code': 'still slow'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertIn('run_math_python', [t['function']['name'] for t in f.snapshots[1]['tools']])
        self.assertEqual([t['function']['name'] for t in f.snapshots[2]['tools']], ['recall_tool_result'])
        self.assertEqual(f.session.call_tool.await_count, 2)

    async def test_math_timeout_retry_is_shared_with_parser(self):
        f = self.fixture
        name = 'run_file_parser_python'
        f.tools[name] = ('my-tools', f.session, NS(name=name, description=name, inputSchema={'type': 'object'}))
        f.results['run_math_python'] = '오류: 실행 시간이 30초를 초과했습니다.'
        f.results[name] = '오류: 실행 시간이 60초를 초과했습니다.'
        f.sequence = [response('run_math_python', {'code': 'slow'}), response(name, {'code': 'slow'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertEqual([t['function']['name'] for t in f.snapshots[2]['tools']], ['recall_tool_result'])

    async def test_math_whole_tool_deadline_allows_only_recall(self):
        f = self.fixture
        f.results['run_math_python'] = '[TOOL_TIMEOUT] 오류: 도구 전체 실행 시간이 120초를 초과했습니다.'
        f.sequence = [response('run_math_python', {'code': 'slow'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertEqual([t['function']['name'] for t in f.snapshots[1]['tools']], ['recall_tool_result'])

    async def test_timeout_preserves_recall_in_same_batch(self):
        f = self.fixture
        f.results['read_document'] = '오류: 실행 시간이 120초를 초과했습니다.'
        batch = response('read_document', {'file_path': 'mock'})
        batch.message.tool_calls.extend(response('recall_tool_result', {'result_id': 'R1'}).message.tool_calls)
        f.sequence = [batch, response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        messages = [m for m in f.snapshots[1]['messages'] if isinstance(m, dict)]
        recalled = next(m for m in messages if m.get('tool_name') == 'recall_tool_result')
        self.assertIn('[R1,', recalled['content'])

    async def test_mcp_timeout_allows_only_recall(self):
        f = self.fixture
        error = f.agent.McpError('mock timeout')
        error.error = NS(code=408)
        f.session.call_tool.side_effect = error
        f.sequence = [response('read_document', {'file_path': 'mock'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertEqual([t['function']['name'] for t in f.snapshots[1]['tools']], ['recall_tool_result'])
        self.assertIn('130', f.content(f.snapshots[1]))

    async def test_client_total_timeout(self):
        f = self.fixture
        f.agent.TOOL_TIMEOUT_SECONDS = .01

        async def blocked(*args, **kwargs):
            await asyncio.sleep(10)

        f.session.call_tool.side_effect = blocked
        f.sequence = [response('read_document', {'file_path': 'mock'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertEqual([t['function']['name'] for t in f.snapshots[1]['tools']], ['recall_tool_result'])

    async def test_recall_on_turn_after_server_deadline(self):
        f = self.fixture
        f.results['read_document'] = 'stored evidence'
        f.results['run_math_python'] = '[TOOL_TIMEOUT] whole tool deadline'
        f.sequence = [response('read_document'), response('run_math_python'),
                      response('recall_tool_result', {'result_id': 'R1'}), response()]
        await f.agent.ask('question', connected_tools=f.tools, use_memory=False)
        self.assertIn('stored evidence', f.content(f.snapshots[3]))
        self.assertEqual(f.session.call_tool.await_count, 2)


if __name__ == '__main__':
    unittest.main()
