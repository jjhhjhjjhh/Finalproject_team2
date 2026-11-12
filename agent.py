"""MCP 도구를 쓰는 Agent.

사용법
  python agent.py --tools          연결된 MCP 도구 목록 보기
  python agent.py "질문"            Agent에게 질문하기
"""
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "qwen3-vl:2b-instruct"
HERE = Path(__file__).parent

# 연결할 MCP 서버: 이름 → 실행 방법
SERVERS = {
    "my-tools": StdioServerParameters(command=sys.executable, args=[str(HERE / "my_server.py")]),   # 직접 만든 서버
    "fetch": StdioServerParameters(command=sys.executable, args=["-m", "mcp_server_fetch"]),        # 공식 서버
}

SYSTEM = ("당신은 도구를 사용해 일을 처리하는 도우미입니다. 필요하면 도구를 호출하고, 결과를 보고 한국어로 짧게 답하세요. "
          "엑셀 표를 만들 때는 create_excel의 csv_text에 첫 줄을 열 이름으로 하는 쉼표 구분 표를 넣으세요.")
MAX_TURNS = 5


async def connect(stack):
    """모든 MCP 서버에 연결하고 도구 목록을 모은다: initialize → tools/list"""
    errlog = open(HERE / "mcp_servers.log", "a", encoding="utf-8")
    tools = {}
    for server_name, params in SERVERS.items():
        read, write = await stack.enter_async_context(stdio_client(params, errlog=errlog))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        for tool in (await session.list_tools()).tools:
            tools[tool.name] = (server_name, session, tool)
    return tools


def to_ollama(tool):
    """MCP 도구 정보 → Ollama tools 형식"""
    return {"type": "function", "function": {
        "name": tool.name, "description": tool.description, "parameters": tool.inputSchema}}


async def show_tools():
    async with AsyncExitStack() as stack:
        for name, (server_name, _, tool) in (await connect(stack)).items():
            print(f"[{server_name}] {name}: {tool.description.strip().splitlines()[0]}")


def check_ollama():
    """Ollama가 켜져 있고 모델이 있는지 먼저 확인한다."""
    try:
        names = [m.model for m in ollama.list().models]
    except Exception:
        print("[ERROR] Ollama에 연결할 수 없습니다. Ollama 앱을 실행한 뒤 다시 시도하세요.")
        return False
    if not any(n.split(":latest")[0] == MODEL for n in names):
        print(f"[ERROR] {MODEL} 모델이 없습니다. 터미널에서 ollama pull {MODEL} 을 실행하세요.")
        return False
    return True


async def ask(question):
    if not check_ollama():
        return
    async with AsyncExitStack() as stack:
        tools = await connect(stack)
        schemas = [to_ollama(tool) for _, _, tool in tools.values()]
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
        print(f"[QUESTION] {question}")
        for turn in range(1, MAX_TURNS + 1):
            last = turn == MAX_TURNS                       # 마지막 차례에는 도구 없이 답하게 한다
            response = ollama.chat(model=MODEL, messages=messages, tools=None if last else schemas,
                                   options={"temperature": 0.3})
            message = response.message
            messages.append(message)
            if not message.tool_calls:
                print(f"[ANSWER] {message.content}")
                return
            for call in message.tool_calls:                # tools/call
                name, args = call.function.name, dict(call.function.arguments)
                server_name = tools[name][0] if name in tools else "?"
                print(f"[TOOL CALL] {server_name}.{name} {json.dumps(args, ensure_ascii=False)}")
                if name not in tools:
                    text = f"없는 도구입니다: {name}"
                else:
                    try:
                        result = await tools[name][1].call_tool(name, args)
                        text = "\n".join(c.text for c in result.content if c.type == "text")
                    except Exception as exc:
                        text = f"도구 실행 오류: {exc}"
                print(f"[TOOL RESULT] {text[:300]}{' ...' if len(text) > 300 else ''}")
                messages.append({"role": "tool", "tool_name": name, "content": text[:4000]})


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        sys.exit("[ERROR] Python 3.10 이상이 필요합니다. 현재: " + sys.version.split()[0])
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == "--tools":
        asyncio.run(show_tools())
    else:
        asyncio.run(ask(" ".join(sys.argv[1:])))
