"""Offline regression tests of real agent/memory code with fake LLM and MCP I/O.

Run: python -m unittest discover -s tests -p test_agent_memory.py -v
No installed MCP/Ollama packages, network, or user memory files are required.
"""
import asyncio
import copy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
NS = types.SimpleNamespace


def load_source(name, filename):
    path = ROOT / filename
    module = types.ModuleType(name)
    module.__file__ = str(path)
    # Read source directly; do not depend on cached bytecode in the user's venv/workspace.
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
    return module


def response(name=None, args=None, answer='answer'):
    calls = [NS(function=NS(name=name, arguments=args or {}))] if name else []
    return NS(message=NS(content='' if name else answer, tool_calls=calls), done_reason='stop')


class AgentMemoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.llm = types.ModuleType('ollama')
        self.llm.list = Mock(return_value=NS(models=[NS(model='qwen3:8b')]))
        self.llm.embed = Mock(side_effect=lambda **kw: NS(embeddings=[[1., 0.] for _ in kw['input']]))
        self.llm.chat = Mock()
        modules = {'ollama': self.llm}
        for name in ('mcp', 'mcp.client', 'mcp.client.stdio', 'mcp.shared', 'mcp.shared.exceptions'):
            modules[name] = types.ModuleType(name)
        modules['mcp'].ClientSession = Mock()
        modules['mcp'].StdioServerParameters = lambda **kw: NS(**kw)
        modules['mcp.client.stdio'].stdio_client = Mock()
        modules['mcp.shared.exceptions'].McpError = type('McpError', (Exception,), {})
        with patch.dict(sys.modules, modules):
            self.memory = load_source('memory_under_test', 'memory.py')
            with patch.dict(sys.modules, {'memory': self.memory}):
                self.agent = load_source('agent_under_test', 'agent.py')
        self.agent.MODEL = 'qwen3:8b'
        self.memory.BASE_DIR = Path(self.tmp.name) / 'memory'
        self.memory.RECORDS_DIR = self.memory.BASE_DIR / 'records'
        self.memory.INDEX_FILE = self.memory.BASE_DIR / 'index.json'
        self.directories = []
        real_temp = tempfile.TemporaryDirectory

        def temporary(**kwargs):
            directory = real_temp(dir=self.tmp.name, **kwargs)
            self.directories.append(Path(directory.name))
            return directory

        self.agent.TemporaryDirectory = temporary
        self.session = NS(call_tool=AsyncMock(side_effect=self.tool_result))
        self.results = {}
        self.tools = {
            name: ('my-tools', self.session, NS(name=name, description=name, inputSchema={'type': 'object'}))
            for name in ('read_document', 'run_math_python', 'send_email')
        }
        self.snapshots = []
        self.sequence = []

        def model(**kwargs):
            self.snapshots.append(copy.deepcopy(kwargs))
            return self.sequence.pop(0)

        self.llm.chat.side_effect = model
        quiet = patch('builtins.print')
        quiet.start()
        self.addCleanup(quiet.stop)

    async def tool_result(self, name, args, **kwargs):
        return NS(content=[NS(type='text', text=self.results.get(name, 'tool output'))], isError=False)

    def content(self, snapshot):
        return '\n'.join(m['content'] for m in snapshot['messages'] if isinstance(m, dict))

    def assert_cleaned(self):
        self.assertTrue(self.directories)
        self.assertTrue(all(not p.exists() for p in self.directories))

    async def test_recall_original_after_recent_history_eviction(self):
        self.results['read_document'] = 'A' * 2500 + ' UNIQUE_MIDDLE_EVIDENCE ' + 'B' * 2500
        self.sequence = [
            response('read_document', {'file_path': 'demo.txt'}),
            response('run_math_python', {'code': '1'}),
            response('run_math_python', {'code': '2'}),
            response('recall_tool_result', {'result_id': 'R1', 'keyword': 'UNIQUE_MIDDLE_EVIDENCE'}),
            response(answer='verified answer'),
        ]
        answer = await self.agent.ask('question', connected_tools=self.tools)
        self.assertEqual(answer, 'verified answer')
        self.assertNotIn('UNIQUE_MIDDLE_EVIDENCE', self.content(self.snapshots[1]))
        old_tools = [m.get('tool_name') for m in self.snapshots[3]['messages'] if isinstance(m, dict)]
        self.assertNotIn('read_document', old_tools)
        self.assertIn('R1', self.content(self.snapshots[3]))
        self.assertIn('UNIQUE_MIDDLE_EVIDENCE', self.content(self.snapshots[4]))
        self.assertEqual(self.session.call_tool.await_count, 3)
        self.assertIn('verified answer', self.memory.retrieve_memories('question'))
        self.assert_cleaned()

    async def test_cache_reuse_and_reset_between_questions(self):
        call = response('read_document', {'file_path': 'same.txt'})
        self.sequence = [call, call, response(), call, response()]
        await self.agent.ask('first', connected_tools=self.tools, use_memory=False)
        self.assertEqual(self.session.call_tool.await_count, 1)
        self.assertIsNone(self.snapshots[2]['tools'])
        await self.agent.ask('second', connected_tools=self.tools, use_memory=False)
        self.assertEqual(self.session.call_tool.await_count, 2)
        self.assertNotIn('R1', self.content(self.snapshots[3]))
        self.assertIn('[R1]', self.content(self.snapshots[4]))
        self.assertEqual(len(set(self.directories)), 2)
        self.assert_cleaned()

    async def test_side_effect_tools_are_not_cached(self):
        call = response('send_email', {'to': 'fake@example.com'})
        self.sequence = [call, call, response()]
        await self.agent.ask('question', connected_tools=self.tools, use_memory=False)
        self.assertEqual(self.session.call_tool.await_count, 2)
        self.assert_cleaned()

    async def test_chat_keeps_connection_and_persists_qa(self):
        closed = []

        async def connect(stack):
            stack.callback(lambda: closed.append(True))
            return self.tools

        self.agent.connect = AsyncMock(side_effect=connect)
        self.sequence = [response(answer='FIRST_ANSWER'), response(answer='SECOND_ANSWER')]
        with patch('builtins.input', side_effect=['second', 'exit']):
            await self.agent.chat('first')
        self.agent.connect.assert_awaited_once()
        self.assertEqual(closed, [True])
        self.assertIn('FIRST_ANSWER', self.content(self.snapshots[1]))
        self.assertEqual(len(list(self.memory.RECORDS_DIR.glob('*.txt'))), 2)
        self.assert_cleaned()

    async def test_evaluation_flags_skip_tools_and_memory(self):
        self.agent.connect = AsyncMock()
        self.agent.retrieve_memories = Mock(side_effect=AssertionError('unexpected memory read'))
        self.agent.save_qa = Mock(side_effect=AssertionError('unexpected memory write'))
        self.sequence = [response()]
        await self.agent.ask('baseline', use_tools=False, use_memory=False)
        self.agent.connect.assert_not_awaited()
        self.agent.retrieve_memories.assert_not_called()
        self.agent.save_qa.assert_not_called()
        self.assertIsNone(self.snapshots[0]['tools'])
        self.assert_cleaned()

    async def test_memory_errors_do_not_break_answer_or_cleanup(self):
        self.agent.retrieve_memories = Mock(side_effect=OSError('read failure'))
        self.agent.save_qa = Mock(side_effect=OSError('write failure'))
        self.sequence = [response()]
        self.assertEqual(await self.agent.ask('question', connected_tools=self.tools), 'answer')
        self.assert_cleaned()

    async def test_model_error_cleans_temporary_records(self):
        self.llm.chat.side_effect = RuntimeError('mock model failure')
        with self.assertRaises(RuntimeError):
            await self.agent.ask('question', connected_tools=self.tools)
        self.assert_cleaned()

    async def test_single_ask_still_owns_its_connection(self):
        closed = []

        async def connect(stack):
            stack.callback(lambda: closed.append(True))
            return self.tools

        self.agent.connect = AsyncMock(side_effect=connect)
        self.sequence = [response()]
        await self.agent.ask('question', use_memory=False)
        self.agent.connect.assert_awaited_once()
        self.assertEqual(closed, [True])
        self.assert_cleaned()

    async def test_tool_memory_index_pagination_and_invalid_ids(self):
        with tempfile.TemporaryDirectory(dir=self.tmp.name) as directory:
            memory = self.agent.ToolResultMemory(Path(directory))
            key = memory.store('read_document', {'file_path': 'demo.txt'}, 'A' * 4000 + 'END_MARKER')
            self.assertEqual(key, 'R1')
            self.assertIn('demo.txt', memory.read(''))
            self.assertIn('END_MARKER', memory.read('R1', offset=3900))
            self.assertNotIn('END_MARKER', memory.read('R1'))
            self.assertNotEqual(memory.read('R999'), memory.read('R1'))


if __name__ == '__main__':
    unittest.main()
