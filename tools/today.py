"""예시 도구: 오늘 날짜 (Asia/Seoul)."""
from datetime import datetime, timedelta, timezone

from tools import tool


@tool
def get_today() -> str:
    """오늘 날짜와 현재 시각(한국 시간)을 반환한다.

    언제 쓰나: 질문에 '현재', '오늘', '최근', '올해'가 들어가 기준일이 필요할 때.

    Returns:
        예: "2026-11-12 (Thu) 10:30 KST"
    """
    now = datetime.now(timezone(timedelta(hours=9)))
    return now.strftime("%Y-%m-%d (%a) %H:%M KST")


if __name__ == "__main__":
    print(get_today())