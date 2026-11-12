"""도구 템플릿 — 복사해서 tools/<도구이름>.py 로 만드세요.
(_ 로 시작하는 파일은 자동 등록되지 않습니다.)
"""
from tools import tool

MAX_CHARS = 20_000


@tool
def my_tool(query: str) -> str:
    """한 줄 요약: 이 도구가 무엇을 하는지.

    언제 쓰나: 어떤 질문일 때 이 도구를 부르면 되는지.

    Args:
        query: 입력 설명

    Returns:
        출력 설명
    """
    try:
        result = f"echo: {query}"  # TODO: 구현
        return result[:MAX_CHARS]
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    print(my_tool("테스트"))
