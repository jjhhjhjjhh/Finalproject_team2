"""Shared deadlines and isolated execution for synchronous local MCP tools."""
import asyncio
import json
import os
import signal
import subprocess
import sys
from functools import wraps
from contextlib import asynccontextmanager
from pathlib import Path

TOOL_EXECUTION_SECONDS = 120
TOOL_RESPONSE_SECONDS = 130
MCP_CONNECTION_SECONDS = 30
MCP_DISCOVERY_SECONDS = 30
TIMEOUT_MARKER = '[TOOL_TIMEOUT]'


@asynccontextmanager
async def deadline(seconds):
    """Bound a block without moving AnyIO context entry into a different task."""
    task = asyncio.current_task()
    expired = False

    def cancel():
        nonlocal expired
        expired = True
        task.cancel()

    timer = asyncio.get_running_loop().call_later(seconds, cancel)
    try:
        yield
    except asyncio.CancelledError:
        if not expired:
            raise
        if hasattr(task, 'uncancel'):
            task.uncancel()
        raise TimeoutError(f'Deadline exceeded: {seconds}s') from None
    finally:
        timer.cancel()


async def stop_process_tree(process):
    """Stop only the tool process and its descendants, including parser children."""
    if process.returncode is not None:
        return
    if sys.platform == 'win32':
        killer = await asyncio.create_subprocess_exec(
            'taskkill', '/PID', str(process.pid), '/T', '/F',
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            await asyncio.wait_for(killer.wait(), 5)
        except asyncio.TimeoutError:
            killer.kill()
            await killer.wait()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    await process.wait()


async def run_isolated(command, payload, timeout=TOOL_EXECUTION_SECONDS):
    started = asyncio.get_running_loop().time()
    options = ({'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32'
               else {'start_new_session': True})
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, **options,
    )
    communication = asyncio.create_task(process.communicate(payload))
    try:
        remaining = max(0, timeout - (asyncio.get_running_loop().time() - started))
        stdout, stderr = await asyncio.wait_for(asyncio.shield(communication), remaining)
        if process.returncode:
            # Do not expose subprocess stderr; libraries may print credentials/URLs.
            return f'오류: 도구 실행 프로세스가 종료되었습니다 (exit={process.returncode}).'
        return json.loads(stdout.decode('utf-8'))
    except asyncio.TimeoutError:
        await stop_process_tree(process)
        return f'{TIMEOUT_MARKER} 오류: 도구 전체 실행 시간이 {timeout}초를 초과했습니다. 실행 프로세스를 중단했습니다.'
    except asyncio.CancelledError:
        await stop_process_tree(process)
        raise
    finally:
        if not communication.done():
            communication.cancel()
        await asyncio.gather(communication, return_exceptions=True)


def isolated_tool(mcp, server_file):
    """Register an async MCP wrapper while preserving direct Python calls for tests."""
    def decorator(function):
        @wraps(function)
        async def invoke(**arguments):
            return await run_isolated(
                [sys.executable, str(Path(server_file).resolve()), '--run-tool', function.__name__],
                json.dumps(arguments, ensure_ascii=False).encode('utf-8'),
            )
        mcp.tool()(invoke)
        return function
    return decorator
