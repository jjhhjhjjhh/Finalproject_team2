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

def load_image(image_path: str) -> bytes:
    """이미지 파일을 읽어 bytes 형태로 반환한다."""

    path = Path(image_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"이미지 파일을 찾을 수 없습니다: {image_path}"
        )

    if path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise ValueError(
            "지원하지 않는 이미지 형식입니다."
        )

    return path.read_bytes()

# 연결할 MCP 서버: 이름 → 실행 방법
SERVERS = {
    "my-tools": StdioServerParameters(command=sys.executable, args=[str(HERE / "my_server.py")]),   # 직접 만든 서버
    "fetch": StdioServerParameters(command=sys.executable, args=["-m", "mcp_server_fetch"]),        # 공식 서버
}

SYSTEM = (
"""
당신은 다양한 문제를 해결하는 범용 AI 에이전트입니다.
사용자의 질문을 분석하고, 필요한 경우 제공된 MCP 도구를 활용하여 정확한 답변을 생성하세요.

[기본 원칙]
1. 사용자의 질문과 요구 조건을 정확히 파악합니다.
2. 자체 지식만으로 해결할 수 있는 문제는 직접 해결합니다.
3. 최신 정보나 외부 사실 확인이 필요한 경우 웹 검색 도구를 활용합니다.
4. 복잡한 수학 계산이 필요한 경우 Python 실행 도구를 활용합니다.
5. 도구 실행 결과를 검토하고, 필요한 경우 추가 도구를 호출합니다.
6. 확인되지 않은 정보를 사실처럼 제시하지 않습니다.
7. 최종 답변은 한국어로 작성합니다.

[이미지 분석]
1. 이미지가 제공되면 이미지의 내용을 먼저 분석합니다.
2. 이미지 속 문자, 건물, 사물, 도형 및 주변 환경의 특징을 파악합니다.
3. 이미지 속 장소나 사물을 식별해야 한다면 시각적 특징을 바탕으로 추론합니다.
4. 정확한 식별이 필요한 경우 웹 검색으로 추가 검증합니다.
5. 불확실한 경우 여러 후보를 비교하고 근거를 확인합니다.

[웹 검색]
1. 최신 정보, 가격, 일정, 인물 정보 등은 웹 검색을 활용합니다.
2. 가능한 경우 공식 홈페이지와 신뢰할 수 있는 자료를 우선합니다.
3. 검색 결과가 부족하면 검색어를 수정해 추가 검색합니다.
4. 서로 다른 출처의 정보가 충돌하면 신뢰성과 날짜를 비교합니다.

[수학 계산]
1. 복잡하거나 정확한 수치 계산이 필요한 경우 Python 도구를 사용합니다.
2. 계산 결과가 문제 조건을 만족하는지 확인합니다.
3. 오류가 발생하면 원인을 분석하고 수정합니다.

[문서 처리]
1. 사용자의 질문을 해결하는 데 문서 자료가 필요하면 웹 검색을 수행합니다.
2. 검색 결과에서 PDF, Word, Excel, CSV, TXT 문서의 다운로드 URL을 발견하면 download_document 도구를 사용할 수 있습니다.
3. 문서를 다운로드한 뒤 read_document 도구로 내용을 확인합니다.
4. 문서의 내용을 분석하여 질문에 답합니다.
5. 문서의 일부만 읽은 경우 전체 내용을 확인한 것처럼 답하지 않습니다.
6. 가능하면 문서의 제목, 출처 URL, 작성 시점을 확인합니다.
7. 문서에 근거한 답변에는 출처를 표시합니다.

[최종 답변]
1. 질문에 대한 답을 명확하게 제시합니다.
2. 필요한 경우 풀이 과정과 판단 근거를 설명합니다.
3. 외부 정보를 활용했다면 출처를 제시합니다.
4. 정보가 부족한 경우 임의로 추측하지 않습니다.


"""
)

MAX_TURNS = 12
MAX_TOOL_RESULT = 15000   # 도구 결과를 LLM에게 넘길 때 최대 글자 수


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



async def ask(question, image_path=None):
    if not check_ollama():
        return
    async with AsyncExitStack() as stack:
        tools = await connect(stack)
        schemas = [to_ollama(tool) for _, _, tool in tools.values()]

        messages = [{"role": "system", "content": SYSTEM}]
        user_message = {"role": "user","content": question}

        # 이미지가 있으면 추가
        if image_path is not None:
            user_message["images"] = [load_image(image_path)]
        messages.append(user_message)
        
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
                messages.append({"role": "tool", "tool_name": name, "content": text[:MAX_TOOL_RESULT]})


if __name__ == "__main__":

    if sys.version_info < (3, 10):
        sys.exit("[ERROR] Python 3.10 이상이 필요합니다.")

    if len(sys.argv) < 2:
        print(__doc__)

    elif sys.argv[1] == "--tools":
        asyncio.run(show_tools())

    elif sys.argv[1] == "--image":

        if len(sys.argv) < 3:
            print("사용법: python agent.py --image 이미지경로 질문")

        else:
            image_path = sys.argv[2]

            question = (
                " ".join(sys.argv[3:])
                if len(sys.argv) > 3
                else "이 이미지를 분석해 줘."
            )

            asyncio.run(ask(question, image_path))

    else:
        asyncio.run(ask(" ".join(sys.argv[1:])))