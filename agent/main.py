"""에이전트 진입점 (뼈대).

사용법:
    python -m agent.main --list-tools
    python -m agent.main "질문"
"""
import argparse

from tools import describe_tools, get_tools


def answer(question: str) -> str:
    # TODO: 에이전트 구현 (아키텍처 미정)
    return f"[미구현] 질문: {question}\n사용 가능 도구: {', '.join(get_tools())}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--list-tools", action="store_true")
    args = p.parse_args()

    if args.list_tools:
        print(describe_tools() or "(등록된 도구 없음)")
        return
    if not args.question:
        p.error("질문을 입력하세요.")
    print(answer(args.question))


if __name__ == "__main__":
    main()
