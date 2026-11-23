"""직접 만든 MCP 서버: 웹페이지 열기 · 위키백과 검색 · 엑셀 파일 만들고 열기"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
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
from PIL import Image, ImageOps

# 문서를 읽을 수 있는 폴더
DOCUMENT_DIR = Path(__file__).resolve().parent / "documents"

# 최대 파일 크기: 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024

# 최대 반환 문자 수
MAX_OUTPUT_LENGTH = 30000
TOOL_TIMEOUT_SECONDS = 120

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
    """웹페이지를 사용자의 브라우저에서 연다. 사용자가 브라우저로 열어 달라고 직접 요청했을 때만 사용한다.
    웹페이지 내용을 읽으려면 이 도구 대신 fetch를 사용한다. url은 http:// 또는 https://로 시작해야 한다."""
    if not url.startswith(("http://", "https://")):
        return "http:// 또는 https://로 시작하는 주소만 열 수 있습니다."
    # 내부 네트워크(localhost, 사설 IP 등) 주소는 열지 않는다
    try:
        host = urlsplit(url).hostname
        if not host:
            return "주소에 호스트 이름이 없습니다."
        for info in socket.getaddrinfo(host, None):
            if not ipaddress.ip_address(info[4][0]).is_global:
                return "내부 네트워크 주소는 열 수 없습니다."
    except (socket.gaierror, ValueError):
        return "주소를 확인할 수 없습니다."
    webbrowser.open(url)
    return f"브라우저에서 열었습니다: {url}"


@mcp.tool()
def search_wikipedia(query: str) -> str:
    """한국어 위키백과에서 검색어와 가장 가까운 문서를 찾아 제목과 요약을 돌려준다."""
    headers = {"User-Agent": "snu-seminar-mcp-lab/1.0"}
    url = ("https://ko.wikipedia.org/w/api.php?action=query&list=search&format=json"
           f"&srlimit=1&srsearch={quote(query)}")
    hits = json.load(urlopen(Request(url, headers=headers), timeout=TOOL_TIMEOUT_SECONDS))["query"]["search"]
    if not hits:
        return "검색 결과가 없습니다."
    title = hits[0]["title"]
    url = f"https://ko.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    summary = json.load(urlopen(Request(url, headers=headers), timeout=TOOL_TIMEOUT_SECONDS))
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
    """이메일을 지정한 수신자에게 보낸다. 사용자가 직접 요청했을 때만 사용한다.
    수신자는 본인(SMTP_USER)과 .env의 EMAIL_ALLOWED_RECIPIENTS에 등록된 주소만 가능하다."""
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

    # 검색 결과 속 지시 등으로 엉뚱한 곳에 메일이 가지 않도록 허용된 수신자에게만 보낸다
    allowed = {
        address.strip().lower()
        for address in os.getenv("EMAIL_ALLOWED_RECIPIENTS", "").split(",")
        if address.strip()
    }
    allowed.add(sender.strip().lower())
    if recipient.lower() not in allowed:
        return ("허용되지 않은 수신자입니다. 보내려면 .env의 EMAIL_ALLOWED_RECIPIENTS에 "
                "주소를 쉼표로 구분해 추가하세요.")
    if len(body) > 10000:
        return "본문이 너무 깁니다 (최대 10,000자)."

    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(host, port, timeout=TOOL_TIMEOUT_SECONDS) as server:
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

MATH_TIMEOUT_SECONDS = 30
# 계산에 필요한 모듈만 import 허용
MATH_ALLOWED_MODULES = {
    "math", "cmath", "decimal", "fractions", "statistics", "random", "itertools", "functools",
    "collections", "operator", "datetime", "calendar", "re", "json", "string", "bisect", "heapq",
    "numpy", "sympy", "scipy", "pandas", "mpmath",
}
# 파일·프로세스·네트워크에 손댈 수 있는 내장 함수는 차단
MATH_BLOCKED_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "input", "breakpoint",
    "globals", "locals", "vars", "getattr", "setattr", "delattr", "memoryview",
}
# numpy·pandas 등에서 파일·네트워크를 다루는 함수 이름 (read_* 는 접두사로 모두 차단)
MATH_BLOCKED_ATTRS = {
    "system", "popen", "remove", "unlink", "rmdir", "rmtree",
    "load", "save", "savez", "loadtxt", "savetxt", "genfromtxt", "fromfile", "tofile",
    "to_csv", "to_excel", "to_pickle", "to_parquet", "to_json", "to_html", "to_sql", "to_hdf", "to_feather",
}


def check_math_code(code: str) -> str | None:
    """실행 전에 코드를 검사한다. 문제가 있으면 오류 메시지, 없으면 None."""
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"문법 오류: {exc}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            modules = []
        for module in modules:
            if module.split(".")[0] not in MATH_ALLOWED_MODULES:
                return f"허용되지 않은 모듈입니다: {module} (계산용 모듈만 사용 가능)"
        if isinstance(node, ast.Name) and node.id in MATH_BLOCKED_NAMES:
            return f"허용되지 않은 함수입니다: {node.id}"
        if isinstance(node, ast.Attribute) and (
            node.attr.startswith(("__", "read_")) or node.attr in MATH_BLOCKED_ATTRS
        ):
            return f"허용되지 않은 속성입니다: {node.attr}"
        # sympify("...")처럼 문자열을 코드로 해석하는 우회를 막는다
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
            "__" in node.value or "import" in node.value
        ):
            return "문자열 안에 '__'나 'import'를 쓸 수 없습니다."
    return None


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
    - import는 계산 모듈만 가능: math, fractions, decimal, statistics, itertools, datetime, numpy, sympy 등
    - 파일 읽기·쓰기, 네트워크, 다른 프로그램 실행은 불가 (문서는 read_document 사용)
    - 결과는 반드시 print()로 출력
    """

    if not code.strip():
        return "오류: 실행할 Python 코드가 없습니다."

    problem = check_math_code(code)
    if problem:
        return f"Python 실행 거부\n{problem}\n계산 모듈(math, fractions, sympy 등)만 써서 다시 작성하세요."

    # API 키 등 환경변수를 넘기지 않고, 프로젝트 밖 임시 폴더에서 실행한다
    env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP") if key in os.environ}
    env.update(PYTHONIOENCODING="utf-8", OPENBLAS_NUM_THREADS="1")

    try:
        with tempfile.TemporaryDirectory(prefix="math-") as workdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    code
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=workdir,
                env=env,
                timeout=MATH_TIMEOUT_SECONDS,
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
        return f"오류: 실행 시간이 {MATH_TIMEOUT_SECONDS}초를 초과했습니다."

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
            timeout=TOOL_TIMEOUT_SECONDS,
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
                timeout=(5, TOOL_TIMEOUT_SECONDS),
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
SERPAPI_IMAGE_LIMIT = 500_000
LENS_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def prepare_lens_image(path: Path) -> tuple[str, bytes, str]:
    content = path.read_bytes()
    if len(content) <= SERPAPI_IMAGE_LIMIT:
        return path.name, content, LENS_IMAGE_TYPES[path.suffix.lower()]

    with Image.open(io.BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    for quality in (88, 78, 68, 58):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        if buffer.tell() <= SERPAPI_IMAGE_LIMIT:
            return f"{path.stem}.jpg", buffer.getvalue(), "image/jpeg"
        image.thumbnail(
            (max(1, image.width * 3 // 4), max(1, image.height * 3 // 4)),
            Image.Resampling.LANCZOS,
        )
    raise ValueError("이미지를 SerpApi의 500KB 제한에 맞게 줄이지 못했습니다.")


def format_lens_results(filename: str, data: dict) -> str:
    sources = []
    seen = set()
    for field, label in (("exact_matches", "일치 후보"), ("visual_matches", "유사 후보")):
        for match in data.get(field) or []:
            url = match.get("link") or ""
            if not url.startswith(("https://", "http://")) or len(url) > 600 or url in seen:
                continue
            seen.add(url)
            title = " ".join((match.get("title") or match.get("source") or "제목 없음").split())
            sources.append(f"- [{label}] {title[:140]}\n  {url}")
            if len(sources) == 4:
                break
        if len(sources) == 4:
            break

    if not sources:
        return f"Google Lens 결과 없음 ({filename}): 확인할 수 있는 출처 링크가 없습니다."
    return f"[Google Lens 검색 결과] 이미지: {filename}\n[관련 웹페이지]\n" + "\n".join(sources)


def request_lens_search(image_id: str, api_key: str) -> requests.Response:
    params = {
        "engine": "google_lens", "image_id": image_id, "type": "all",
        "hl": "ko", "country": "kr", "api_key": api_key,
    }
    for attempt in range(2):
        try:
            return requests.get(
                "https://serpapi.com/search", params=params,
                timeout=(5, TOOL_TIMEOUT_SECONDS), allow_redirects=False,
            )
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            raise
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            if attempt == 1:
                raise


@mcp.tool()
def google_lens_search(image_path: str) -> str:
    """
    첨부 이미지를 SerpApi에 업로드해 Google Lens의 일치·유사 이미지 출처를 찾는다.
    image_path에는 안내된 첨부 이미지 파일명(예: search_123456.jpg)을 전달한다.
    결과의 제목과 링크를 인용하고, 이미지의 출처가 불확실하면 이를 밝힌다.
    """
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        return "오류: .env에 SERPAPI_API_KEY를 설정하세요."

    path = (IMAGE_DIR / image_path).resolve()
    if not path.is_relative_to(IMAGE_DIR.resolve()):
        return "오류: images 폴더 외부 파일은 사용할 수 없습니다."
    if not path.is_file():
        return f"오류: 이미지 파일이 없습니다: {image_path}"
    if path.suffix.lower() not in LENS_IMAGE_TYPES:
        return "오류: 지원하지 않는 이미지 형식입니다."

    try:
        upload_image = prepare_lens_image(path)
    except (OSError, ValueError, Image.DecompressionBombError):
        return "오류: SerpApi에 업로드할 이미지를 읽거나 500KB 이하로 변환할 수 없습니다."

    stage = "이미지 업로드"
    try:
        upload = requests.post(
            "https://serpapi.com/image",
            data={"api_key": api_key},
            files={"image": upload_image},
            timeout=(5, TOOL_TIMEOUT_SECONDS),
            allow_redirects=False,
        )
        upload.raise_for_status()
        uploaded = upload.json()
        image_id = uploaded.get("image_id")
        if uploaded.get("error") or not image_id:
            return "오류: SerpApi가 이미지 업로드를 완료하지 못했습니다."

        stage = "Google Lens 검색"
        search = request_lens_search(image_id, api_key)
        search.raise_for_status()
        data = search.json()
        if data.get("error"):
            return "오류: SerpApi가 Google Lens 검색을 완료하지 못했습니다."
        return format_lens_results(path.name, data)
    except requests.Timeout:
        return f"오류: SerpApi {stage} 시간이 초과되었습니다."
    except requests.HTTPError as exc:
        status = exc.response.status_code
        if status in (401, 403):
            return "오류: SerpApi 인증에 실패했습니다. .env의 SERPAPI_API_KEY를 확인하세요."
        if status == 429:
            return "오류: SerpApi 요청 한도에 도달했습니다."
        return f"오류: SerpApi {stage} 실패 (HTTP {status})."
    except requests.exceptions.JSONDecodeError:
        return f"오류: SerpApi {stage} 응답을 읽을 수 없습니다."
    except requests.exceptions.SSLError:
        return f"오류: SerpApi {stage} 연결의 TLS 인증서 검증 또는 협상이 실패했습니다."
    except requests.exceptions.ProxyError:
        return f"오류: SerpApi {stage} 요청이 프록시에 연결하지 못했습니다."
    except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ContentDecodingError):
        return f"오류: SerpApi {stage} 응답이 전송 중 끊겼거나 손상됐습니다."
    except requests.RequestException as exc:
        # 요청 URL 대신 예외 유형과 시스템 오류 번호만 표시해 API 키 노출을 막는다.
        details = [type(exc).__name__]
        cause = exc.__cause__ or exc.__context__
        while cause:
            details.append(type(cause).__name__)
            error_number = getattr(cause, "winerror", None) or getattr(cause, "errno", None)
            if error_number is not None:
                details.append(str(error_number))
                break
            cause = cause.__cause__ or cause.__context__
        return f"오류: SerpApi {stage} 요청 실패 ({', '.join(details)})."


if __name__ == "__main__":
    mcp.run()
