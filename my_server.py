"""직접 만든 MCP 서버: 웹페이지 열기 · 위키백과 검색 · 엑셀 파일 만들고 열기"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-tools")
OUTPUT_DIR = Path(__file__).parent / "outputs"


def open_with_default_app(path):
    """운영체제의 기본 프로그램으로 파일을 연다 (엑셀 파일 → Excel 등)."""
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


@mcp.tool()
def open_webpage(url: str) -> str:
    """웹페이지를 사용자의 브라우저에서 연다. url은 http:// 또는 https://로 시작해야 한다."""
    if not url.startswith(("http://", "https://")):
        return "http:// 또는 https://로 시작하는 주소만 열 수 있습니다."
    webbrowser.open(url)
    return f"브라우저에서 열었습니다: {url}"


@mcp.tool()
def search_wikipedia(query: str) -> str:
    """한국어 위키백과에서 검색어와 가장 가까운 문서를 찾아 제목과 요약을 돌려준다."""
    headers = {"User-Agent": "snu-seminar-mcp-lab/1.0"}
    url = ("https://ko.wikipedia.org/w/api.php?action=query&list=search&format=json"
           f"&srlimit=1&srsearch={quote(query)}")
    hits = json.load(urlopen(Request(url, headers=headers), timeout=15))["query"]["search"]
    if not hits:
        return "검색 결과가 없습니다."
    title = hits[0]["title"]
    url = f"https://ko.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    summary = json.load(urlopen(Request(url, headers=headers), timeout=15))
    return f"제목: {title}\n요약: {summary.get('extract', '')}"


@mcp.tool()
def create_excel(filename: str, csv_text: str) -> str:
    """표를 엑셀 파일(.xlsx)로 저장하고 엑셀 프로그램으로 연다.
    csv_text는 쉼표로 구분한 표이며 첫 줄은 열 이름이다. 예: '요일,할 일\\n월,자료 조사\\n화,회의'"""
    from openpyxl import Workbook

    name = re.sub(r"[^\w가-힣-]", "_", Path(filename).stem) or "table"
    rows = [r for r in csv.reader(io.StringIO(csv_text.replace("\\n", "\n"))) if r]
    if not rows:
        return "표 내용이 비어 있습니다."
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append([cell.strip() for cell in row])
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.xlsx"
    wb.save(path)
    try:
        open_with_default_app(path)
        opened = "엑셀로 열었습니다"
    except Exception as exc:
        opened = f"파일은 저장했지만 열지 못했습니다 ({exc})"
    return f"{len(rows) - 1}행 표를 저장했습니다: outputs/{path.name} · {opened}"


if __name__ == "__main__":
    mcp.run()
