# 도구 추가 규칙

> 초안 — 레포 초기 템플릿 기준, 팀 합의 후 확정

## 한 파일 = 한 도구

```python
# tools/example_tool.py
from tools import tool

@tool
def example_tool(query: str) -> str:
    """이 도구가 무엇을 하는지 한 줄 요약.

    Args:
        query: 입력 설명

    Returns:
        출력 설명
    """
    ...
```

`@tool`만 붙이면 `tools/__init__.py`가 자동으로 등록한다. 다른 파일을 고칠 필요 없음.

## 지킬 것
1. **docstring 필수** — LLM은 이것만 보고 도구를 쓴다. 언제 쓰는지, 입력, 출력을 명확히
2. **반환값은 문자열** (또는 문자열로 바꾸기 쉬운 dict/list)
3. **실패해도 예외로 죽지 않기** — `"ERROR: <이유>"` 문자열 반환
4. **출력 길이 제한** — 긴 텍스트는 잘라서 반환 (LLM 컨텍스트 보호)
5. **시간 제한** — 네트워크 호출에는 `timeout=` 필수
6. **API 키는 `os.environ`에서** — 코드에 직접 쓰지 않기, `.env.example`에 키 이름 추가
7. **새 패키지를 쓰면 `requirements.txt`에 추가**
8. 파일 맨 아래 `if __name__ == "__main__":`에 동작 확인 코드

## 테스트
```bash
python -m tools.<파일이름>         # 각 도구 단독 실행
python -m agent.main --list-tools   # 등록 확인
```

## 아이디어 목록
Issues → `tool-idea` 라벨로 올리기. 만들기 시작하면 본인을 Assignee로.
