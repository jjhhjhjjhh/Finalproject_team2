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
import smtplib
import ssl
import os

import requests

from dotenv import load_dotenv

load_dotenv()

from email.message import EmailMessage
from datetime import datetime
from zoneinfo import ZoneInfo


from mcp.server.fastmcp import FastMCP

import csv
from pathlib import Path

import fitz
from docx import Document
from openpyxl import load_workbook

import ipaddress
import socket
import uuid

from urllib.parse import urljoin, urlsplit
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 문서를 읽을 수 있는 폴더
DOCUMENT_DIR = Path(__file__).resolve().parent / "documents"

# 최대 파일 크기: 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024

# 최대 반환 문자 수
MAX_OUTPUT_LENGTH = 30000

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

@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """이메일을 지정한 수신자에게 보낸다."""
    recipient = to.strip()

    if not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+", recipient):
        return "수신자에는 이메일 주소 하나를 입력하세요."
    if "\r" in subject or "\n" in subject:
        return "제목에 줄바꿈을 넣을 수 없습니다."

    sender = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    host = "smtp.gmail.com"
    port = 587

    if not sender or not password:
        return "SMTP_USER와 SMTP_PASSWORD 환경 변수를 먼저 설정하세요."

    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(sender, password)
            server.send_message(msg)

        return f"이메일을 보냈습니다: {recipient}"

    except (ValueError, OSError, smtplib.SMTPException) as exc:
        return f"이메일 전송에 실패했습니다: {exc}"

@mcp.tool()
def current_datetime(timezone_name: str = "Asia/Seoul") -> str:
    """현재 날짜와 시각을 지정한 시간대 기준으로 알려준다. 예: Asia/Seoul"""
    try:
        now = datetime.now(ZoneInfo(timezone_name))
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return f"알 수 없는 시간대입니다: {timezone_name}"

@mcp.tool()
def run_math_python(code: str) -> str:
    """
    LLM이 작성한 Python 코드를 실행하고 결과를 반환한다.

    사용 목적:
    - 수학 계산
    - 미분 및 적분
    - 행렬 연산
    - 확률과 통계
    - 수치해석

    제한:
    - 실행 시간 최대 30초
    """

    if not code.strip():
        return "오류: 실행할 Python 코드가 없습니다."

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                code
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return (
                "Python 실행 실패\n"
                f"오류 내용:\n{result.stderr[:4000]}"
            )

        output = result.stdout.strip()

        if not output:
            return (
                "코드가 정상적으로 실행되었지만 출력이 없습니다.\n"
                "최종 결과를 print()로 출력하세요."
            )

        return f"Python 실행 성공\n결과:\n{output[:4000]}"

    except subprocess.TimeoutExpired:
        return "오류: 실행 시간이 30초를 초과했습니다."

    except Exception as e:
        return f"Python 실행 오류: {type(e).__name__}: {e}"

@mcp.tool()
def web_search(query: str) -> str:
    """
    인터넷에서 웹 문서와 관련 이미지 URL을 검색한다.
    """

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return "오류: TAVILY_API_KEY가 설정되지 않았습니다."

    if not query.strip():
        return "오류: 검색어가 비어 있습니다."

    url = "https://api.tavily.com/search"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": 5,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": True
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        images = data.get("images") or []
        image_urls = [
            image if isinstance(image, str) else image.get("url")
            for image in images
        ]
        image_urls = [url for url in image_urls if url]
        if not results and not image_urls:
            return "검색 결과가 없습니다."

        output = []

        if image_urls:
            output.append("이미지 URL:\n" + "\n".join(image_urls[:5]) + "\n")
        for i, result in enumerate(results, start=1):

            title = result.get("title", "")
            link = result.get("url", "")
            content = result.get("content", "")

            output.append(
                f"[{i}] {title}\n"
                f"URL: {link}\n"
                f"내용: {content}\n"
            )

        return "\n".join(output)

    except requests.exceptions.Timeout:
        return "오류: 웹 검색 요청 시간이 초과되었습니다."

    except requests.exceptions.RequestException as e:
        return f"웹 검색 오류: {e}"

    except ValueError:
        return "오류: 검색 결과를 JSON으로 해석하지 못했습니다."

@mcp.tool()
def read_document(file_path: str) -> str:
    """
    다양한 형식의 문서를 자동으로 읽고 텍스트를 추출한다.

    지원 형식:
    - PDF (.pdf)
    - Word (.docx)
    - Excel (.xlsx)
    - CSV (.csv)
    - Text (.txt)

    사용 목적:
    - 논문 및 보고서 분석
    - 문서 내용 요약
    - 문서 내 정보 검색
    - 표 데이터 분석
    - 문서 기반 질의응답

    file_path:
        documents 폴더를 기준으로 한 상대경로
        예: report.pdf, data/table.xlsx

    반환값:
        문서에서 추출한 텍스트
    """

    try:
        # 1. 문서 폴더 생성
        DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

        # 2. 파일 경로 검증
        path = (DOCUMENT_DIR / file_path).resolve()

        # 허용된 폴더 외부 접근 방지
        if not path.is_relative_to(DOCUMENT_DIR.resolve()):
            return "오류: documents 폴더 외부의 파일은 읽을 수 없습니다."

        # 3. 파일 존재 여부 확인
        if not path.is_file():
            return f"오류: 파일을 찾을 수 없습니다: {file_path}"

        # 4. 파일 크기 확인
        if path.stat().st_size > MAX_FILE_SIZE:
            return "오류: 파일 크기가 20MB를 초과합니다."

        # 5. 확장자 확인
        extension = path.suffix.lower()

        output = []

        # =========================
        # PDF
        # =========================
        if extension == ".pdf":

            with fitz.open(path) as doc:

                for i, page in enumerate(doc):

                    text = page.get_text()

                    output.append(
                        f"\n[페이지 {i + 1}]\n{text}"
                    )

        # =========================
        # Word
        # =========================
        elif extension == ".docx":

            doc = Document(path)

            # 본문 추출
            output.append("[본문]")

            for paragraph in doc.paragraphs:

                if paragraph.text.strip():
                    output.append(paragraph.text)

            # 표 추출
            for table_num, table in enumerate(doc.tables, 1):

                output.append(f"\n[표 {table_num}]")

                for row in table.rows:

                    cells = [
                        cell.text.strip()
                        for cell in row.cells
                    ]

                    output.append(" | ".join(cells))

        # =========================
        # Excel
        # =========================
        elif extension == ".xlsx":

            wb = load_workbook(
                path,
                read_only=True,
                data_only=True
            )

            try:
                for sheet in wb.worksheets:

                    output.append(
                        f"\n[시트: {sheet.title}]"
                    )

                    for row in sheet.iter_rows(
                        values_only=True
                    ):

                        values = [
                            str(cell) if cell is not None else ""
                            for cell in row
                        ]

                        output.append(" | ".join(values))

            finally:
                wb.close()

        # =========================
        # CSV
        # =========================
        elif extension == ".csv":

            with open(
                path,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as f:

                reader = csv.reader(f)

                for row in reader:
                    output.append(" | ".join(row))

        # =========================
        # TXT
        # =========================
        elif extension == ".txt":

            with open(
                path,
                "r",
                encoding="utf-8-sig"
            ) as f:

                output.append(f.read())

        # =========================
        # 지원하지 않는 형식
        # =========================
        else:
            return (
                f"지원하지 않는 파일 형식입니다: {extension}\n"
                "지원 형식: PDF, DOCX, XLSX, CSV, TXT"
            )

        # 6. 결과 통합
        result = "\n".join(output)

        if not result.strip():
            return (
                "문서를 읽었지만 추출된 텍스트가 없습니다. "
                "스캔된 이미지 문서일 수 있습니다."
            )

        # 7. 출력 크기 제한
        if len(result) > MAX_OUTPUT_LENGTH:

            result = (
                result[:MAX_OUTPUT_LENGTH]
                + "\n\n[주의: 문서가 길어 일부 내용이 생략되었습니다.]"
            )

        return (
            f"파일명: {path.name}\n"
            f"파일 형식: {extension}\n"
            f"------------------------\n"
            f"{result}"
        )

    except Exception as e:

        return (
            f"문서 읽기 오류: "
            f"{type(e).__name__}: {e}"
        )
    
DOCUMENT_DIR = Path(__file__).resolve().parent / "documents"

# 다운로드 최대 크기: 20MB
MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024

# 지원하는 파일 형식
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".txt"
}

# MIME 타입별 확장자
CONTENT_TYPES = {
    "application/pdf": ".pdf",

    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document": ".docx",

    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet": ".xlsx",

    "text/csv": ".csv",
    "text/plain": ".txt"
}


def validate_public_url(url: str) -> None:
    """공개 HTTPS 주소인지 기본적인 검사를 수행한다."""

    parsed = urlsplit(url)

    if parsed.scheme != "https":
        raise ValueError("HTTPS 주소만 허용합니다.")

    if not parsed.hostname:
        raise ValueError("호스트 이름이 없습니다.")

    if parsed.username or parsed.password:
        raise ValueError("인증 정보가 포함된 URL은 허용하지 않습니다.")

    # DNS 조회 후 공인 IP 주소인지 확인
    addresses = socket.getaddrinfo(
        parsed.hostname,
        parsed.port or 443,
        type=socket.SOCK_STREAM
    )

    if not addresses:
        raise ValueError("서버 주소를 확인할 수 없습니다.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError(
                "내부 네트워크 또는 비공개 주소는 허용하지 않습니다."
            )


@mcp.tool()
def download_document(url: str) -> str:
    """
    인터넷에서 문서를 다운로드하여 documents 폴더에 저장한다.

    지원 형식:
    - PDF
    - Word (.docx)
    - Excel (.xlsx)
    - CSV
    - TXT

    사용 목적:
    - 웹 검색으로 발견한 문서 다운로드
    - 공식 홈페이지의 자료 수집
    - 논문 및 보고서 다운로드
    - 통계 자료 다운로드

    제한:
    - HTTPS만 허용
    - 최대 20MB
    - 지원하는 문서 형식만 저장

    다운로드 후 반환된 파일명을 read_document에 전달하면
    문서 내용을 읽을 수 있다.
    """

    try:
        DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

        current_url = url
        response = None

        # 리다이렉트도 각각 검사
        for _ in range(5):

            validate_public_url(current_url)

            response = requests.get(
                current_url,
                stream=True,
                timeout=(5, 20),
                allow_redirects=False,
                headers={
                    "User-Agent": "Team2-DocumentAgent/1.0"
                }
            )

            if response.status_code in (301, 302, 303, 307, 308):

                location = response.headers.get("Location")
                response.close()

                if not location:
                    return "오류: 리다이렉트 주소가 없습니다."

                current_url = urljoin(current_url, location)
                continue

            break

        else:
            return "오류: 리다이렉트 횟수가 너무 많습니다."

        try:
            response.raise_for_status()

            # 서버가 알려주는 파일 크기 확인
            content_length = response.headers.get("Content-Length")

            if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
                return "오류: 파일 크기가 20MB를 초과합니다."

            # Content-Type 확인
            content_type = response.headers.get(
                "Content-Type", ""
            ).split(";")[0].strip().lower()

            # URL 확장자
            extension = Path(
                urlsplit(current_url).path
            ).suffix.lower()

            # URL에 확장자가 없다면 Content-Type 활용
            if extension not in SUPPORTED_EXTENSIONS:
                extension = CONTENT_TYPES.get(content_type)

            if extension not in SUPPORTED_EXTENSIONS:
                return (
                    "지원하지 않는 문서 형식입니다.\n"
                    f"Content-Type: {content_type}"
                )

            # 파일명 생성: 기존 파일 덮어쓰기 방지
            filename = f"download_{uuid.uuid4().hex[:12]}{extension}"

            path = DOCUMENT_DIR / filename

            total_size = 0

            # 파일 다운로드
            try:
                with open(path, "xb") as f:

                    for chunk in response.iter_content(
                        chunk_size=8192
                    ):

                        if not chunk:
                            continue

                        total_size += len(chunk)

                        if total_size > MAX_DOWNLOAD_SIZE:
                            raise ValueError(
                                "파일 크기가 20MB를 초과합니다."
                            )

                        f.write(chunk)

            except Exception:
                path.unlink(missing_ok=True)
                raise

            return (
                "문서 다운로드 성공\n"
                f"파일명: {filename}\n"
                f"파일 크기: {total_size:,} bytes\n"
                f"원본 URL: {current_url}\n\n"
                f"read_document(file_path='{filename}')로 "
                "내용을 읽을 수 있습니다."
            )

        finally:
            response.close()

    except requests.exceptions.RequestException as e:
        return f"다운로드 오류: {e}"

    except (ValueError, OSError, socket.gaierror) as e:
        return f"다운로드 실패: {e}"

IMAGE_DIR = Path(__file__).resolve().parent / "images"


@mcp.tool()
async def google_lens_search(image_path: str) -> str:
    """
    Google Lens를 이용해 이미지 역검색을 수행한다.

    - images 폴더의 이미지를 Google Lens에 업로드
    - 이미지와 관련된 검색 결과 수집
    - 검색 화면 텍스트와 웹페이지 URL 반환

    image_path 예시: search_123456.jpg
    """

    try:
        # 1. 이미지 파일 검사
        path = (IMAGE_DIR / image_path).resolve()

        if not path.is_relative_to(IMAGE_DIR.resolve()):
            return "오류: images 폴더 외부 파일은 사용할 수 없습니다."

        if not path.is_file():
            return f"오류: 이미지 파일이 없습니다: {path}"

        if path.suffix.lower() not in {
            ".jpg", ".jpeg", ".png", ".webp"
        }:
            return "오류: 지원하지 않는 이미지 형식입니다."

        if path.stat().st_size > 10 * 1024 * 1024:
            return "오류: 이미지 크기가 10MB를 초과합니다."

        # 2. 비동기 Playwright 실행
        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=False
            )

            try:
                page = await browser.new_page(
                    locale="ko-KR",
                    viewport={
                        "width": 1280,
                        "height": 900
                    }
                )

                # 3. Google Lens 접속
                await page.goto(
                    "https://lens.google.com/",
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                # 4. 이미지 업로드 요소 찾기
                upload = page.locator(
                    'input[type="file"]'
                ).first

                try:
                    await upload.wait_for(
                        state="attached",
                        timeout=10000
                    )

                except PlaywrightTimeoutError:
                    return (
                        "오류: Google Lens 이미지 업로드 "
                        "입력란을 찾지 못했습니다."
                    )

                # 5. 이미지 업로드
                await upload.set_input_files(str(path))

                # 6. 검색 결과 로딩
                try:
                    await page.wait_for_url(
                        "**/search?**",
                        timeout=15000
                    )
                except PlaywrightTimeoutError:
                    pass

                await page.wait_for_timeout(3000)

                # 7. 검색 결과 텍스트 추출
                page_text = await page.locator(
                    "body"
                ).inner_text(timeout=15000)

                # 8. 검색 결과 링크 추출
                links = await page.locator(
                    "a[href]"
                ).evaluate_all(
                    """elements => elements.map(a => ({
                        title: (
                            a.innerText ||
                            a.getAttribute('aria-label') ||
                            ''
                        ).trim(),
                        url: a.href
                    }))"""
                )

                output = []
                seen = set()

                for link in links:

                    url = link.get("url", "")
                    title = link.get("title", "")

                    if not url.startswith(
                        ("https://", "http://")
                    ):
                        continue

                    host = (
                        urlsplit(url).hostname or ""
                    ).lower()

                    # Google 내부 링크 제외
                    if (
                        host == "google.com"
                        or host.endswith(".google.com")
                        or host == "google.co.kr"
                        or host.endswith(".google.co.kr")
                        or host == "gstatic.com"
                        or host.endswith(".gstatic.com")
                    ):
                        continue

                    if url in seen:
                        continue

                    seen.add(url)

                    output.append(
                        f"제목: {title or '제목 없음'}\n"
                        f"URL: {url}"
                    )

                    if len(output) >= 10:
                        break

                # 9. 결과 반환
                return (
                    "[Google Lens 검색 결과]\n"
                    f"이미지: {path.name}\n"
                    f"검색 URL: {page.url}\n\n"
                    "[검색 화면 텍스트]\n"
                    f"{page_text[:5000]}\n\n"
                    "[관련 웹페이지]\n"
                    + (
                        "\n\n".join(output)
                        if output
                        else "관련 웹페이지를 추출하지 못했습니다."
                    )
                )

            finally:
                await browser.close()

    except PlaywrightTimeoutError:
        return "오류: Google Lens 검색 시간이 초과되었습니다."

    except Exception as e:
        return (
            "Google Lens 검색 오류: "
            f"{type(e).__name__}: {e}"
        )



if __name__ == "__main__":
    mcp.run()
