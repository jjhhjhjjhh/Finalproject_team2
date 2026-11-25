# QA AI Agent

> Language, AI, and Robots (2026-2) 기말 프로젝트
> 텍스트로 주어진 물음에 답하는 AI Agent

---

## 목차

1. [Project Overview](#project-overview)
2. [Background](#background)
3. [Project Goal](#project-goal)
4. [Key Features](#key-features)
5. [System Flow](#system-flow)
6. [Team](#team)
7. [Git Convention](#git-convention)
8. [Tech Stack](#tech-stack)
9. [Repository Structure](#repository-structure)
10. [Development Roadmap](#development-roadmap)
11. [Installation and Usage](#installation-and-usage)
12. [Documentation](#documentation)
13. [Expected Output](#expected-output)
14. [Evaluation Metrics](#evaluation-metrics)
15. [Known Issues / Operational Notes](#known-issues--operational-notes)

---

## Project Overview

텍스트로 주어진 물음에 답하는 AI Agent 시스템.

| 항목 | 내용 |
|---|---|
| 과목 | Language, AI, and Robots (2026-2) |
| 기간 | 2026.11.12 ~ 2026.12.02 |
| 형태 | 팀별 코드 제출 → TA 환경에서 실제 미션 수행 → 결과 발표 |
| 순위 | 가장 많이 푼 팀 우승, 동점이면 더 빨리 푼 팀 |

## Background

기존 전산 시스템(rule-based, end-to-end NN)이 이미 있는데도 AI Agent를 쓰는 이유는
처음 본 상황(long-tail cases), 불확실성이 높은 상황에서 판단을 내리기 위함이다.

## Project Goal

과제 예시 문제 유형을 포함해, 히든 미션과 각 팀이 출제한 문제셋을 최대한 많이, 빠르게 푼다.

- 예시 1: 주어진 전제로부터 결론 도출 및 논리적 추론 과정 설명 (삼단논법)
- 예시 2: 최신 사실 조사 + 공식 출처 제시 (2026 노벨 물리학상)
- 예시 3: 현재 데이터 조회 + 계산 + 기준일·출처 + 표 (국고채 금리 복리 계산)

> 세부 목표 추가 예정

## Key Features

> 아이디어 단계 — 확정 후 추가 예정

| 아이디어 | 내용 | 상태 |
|---|---|---|
| 연결하고 싶은 도구 | 사용 빈도가 적은 확장자를 여는 툴 | 아이디어 |
| 포함하고 싶은 데이터 | 인터넷 검색으로도 잘 안 나오는 지엽적인 정보 (예: 아프리카 변방 마을 인구 수) | 아이디어 |

## System Flow

> 추가 예정 (아키텍처 미확정)

## Team

| 이름 | 역할 | GitHub |
|---|---|---|
| 모근홍 | 팀장 | @ |
| 김주현 | GitHub 협업 공간 관리 | @ |
| 김민호 | | @ |
| 김태은 | | @ |

- 발표 2명: 기술적 부분 / 기술 외 부분 분담 (담당자 추가 예정)

## Git Convention

> 초안 — 팀 합의 후 확정

**브랜치**: `tool/<이름>`, `agent/<기능>`, `eval/<내용>`, `docs/<내용>`

**커밋 메시지**: `<type>: <내용>`

| type | 의미 |
|---|---|
| `feat` | 기능 추가 |
| `tool` | 도구 추가·수정 |
| `fix` | 버그 수정 |
| `eval` | 평가 관련 |
| `docs` | 문서 |
| `chore` | 설정, 패키지 등 |

## Tech Stack

> 수업 Week 4 MCP 실습 코드 기준 — 확정 시 갱신

| 분류 | 내용 |
|---|---|
| Language | Python 3.10 이상 |
| Tool 연결 | MCP (Model Context Protocol) — `mcp>=1.10,<2`, `mcp-server-fetch` |
| LLM 실행 | Ollama (로컬) |
| 실습 코드 모델 | `qwen3-vl:2b-instruct` |
| 대회용 모델 | 미정 — `Qwen3.8-27B` 이하 로컬 모델만 가능 ([모델 사용 규정](#모델-사용-규정)) |

## Repository Structure

> 수업 실습 코드 기준 — 구조 확정 시 갱신

```
.
├── agent.py          # MCP 서버에 연결해 도구를 쓰는 Agent (Host + Client)
├── my_server.py      # 직접 만든 MCP 서버 — 도구는 여기에 추가
├── eval/             # 평가 문제셋
├── docs/             # 계획, 회의록
├── .github/          # 이슈·PR 템플릿
└── requirements.txt
```

`agent.py`, `my_server.py`는 수업 Week 4 MCP 실습 코드를 그대로 가져온 것.

## Development Roadmap

| 기간 | 내용 |
|---|---|
| 11/12 ~ 다음 주 | 도구 아이디어 공유 → 도구 만들기 → 모아서 연결하기 |
| 그 다음 주 | 성능 평가 지표 만들기 → 에이전트 성능 평가 → 완성 |
| **11/25 (수) 자정** | **팀별 코드 제출** |
| ~11/30 (월) | 연구실 방문해 실제 미션 수행 |
| 12/2 (수) | 결과 발표 (팀별 10분) |

## Installation and Usage

### 준비

Python 3.10 이상, Ollama 앱 실행 + 모델 설치 필요.

**macOS / Linux**
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen3.8:27b
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
ollama pull qwen3.8:27b
```

### 실행

macOS / Linux는 `.venv/bin/python`, Windows는 `.\.venv\Scripts\python.exe`

```bash
.venv/bin/python agent.py --tools                                  # 연결된 도구 목록
.venv/bin/python agent.py "위키백과에서 서울대학교를 찾아서 두 문장으로 알려줘"   # 질문하기
.venv/bin/python agent.py --image "이미지 파일 디렉토리\이미지.jpg" "이 이미지의 장소가 어딘지 한문장으로 알려줘" #이미지 첨부해 질문하기
```

첨부 이미지의 출처나 유사 이미지를 찾으려면 프로젝트의 `.env`에 `SERPAPI_API_KEY=발급받은_키`를 설정하고, `--image`와 함께 “Google Lens로 이 이미지의 출처를 찾아 링크를 알려줘”라고 질문하세요. Lens 검색 시 첨부 이미지를 SerpApi에 업로드합니다. 500KB를 넘는 파일은 업로드용 사본의 크기를 줄입니다.

### 도구 안전장치

TA 컴퓨터에서 돌아가므로, 검색 결과 속 지시(프롬프트 인젝션) 등으로 위험한 동작을 하지 않게 제한해 두었다.

| 도구 | 제한 |
|---|---|
| `run_math_python` | 계산 모듈(math, fractions, numpy, sympy 등)만 import 가능 · 파일/네트워크/프로그램 실행 차단 · API 키 없는 환경, 임시 폴더에서 30초 제한 |
| `send_email` | 본인(`SMTP_USER`)과 허용 수신자에게 즉시 발송 또는 `send_at`으로 예약 |
| `schedule_email` | 날짜·시각과 시간대를 지정하여 이메일 예약 |
| `list_scheduled_emails` | 예약 ID, 상태, 시각과 실패 이유 조회 |
| `cancel_scheduled_email` | 아직 발송을 시작하지 않은 예약 취소 |
| `open_webpage` | 사용자가 직접 요청할 때만 · localhost·사설 IP 등 내부 주소 차단 |
| `run_file_parser_python` | documents·임시 폴더 밖 파일 읽기·쓰기 차단 · 파일 삭제·이름 변경, 네트워크, 프로그램 실행 차단 · API 키 없는 환경에서 60초 제한 |

### 이메일 예약 사용

`python agent.py` 또는 `python agent.py "내일 오전 9시에 이메일을 보내 줘"`로 실행하면
대화 세션이 유지됩니다. 수신자·제목·본문을 함께 알려 주세요. 종료는 `exit` 또는 `quit`입니다.
이미지 질문도 답변 후 대화 세션을 유지합니다. Python에서 직접 호출하는 `ask()`는 기존처럼
한 번만 실행되므로 예약을 계속 처리하려면 `chat()` 또는 상시 MCP 서버를 사용하세요.

`send_email(to, subject, body)`는 즉시 발송하고,
`send_email(to, subject, body, send_at="2027-01-02 09:00", timezone_name="Asia/Seoul")`은 예약합니다.
`schedule_email`도 동일한 예약 저장 기능을 제공합니다. 별도 워커 파일을 실행할 필요가 없습니다.

예약 데이터는 기본적으로 `data/scheduled_emails.sqlite3`에 저장됩니다.
`SCHEDULED_EMAIL_DB`로 변경할 수 있으며 상대 경로는 프로젝트 폴더 기준입니다.
서버는 시작 시와 이후 약 10초 간격으로 발송할 예약을 확인합니다.
**대화 세션/MCP 서버를 종료하거나 PC가 꺼지거나 절전 상태이면 발송되지 않습니다.**
종료 중 시각이 지난 `pending` 예약은 다음 서버 실행 때 발송됩니다.
이미 발송을 시작한 `sending` 상태에서 강제 종료된 경우와 `failed` 상태는 자동 재시도하지 않습니다.
중복 발송을 막기 위해 수신 여부를 확인한 뒤 새로 예약하세요.

SMTP는 기본적으로 Gmail의 587 포트와 STARTTLS를 사용합니다.
`SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_ALLOWED_RECIPIENTS` 설정이 필요하며,
허용 수신자는 예약 저장 시점과 발송 직전에 검사합니다.

실제 이메일 없이 검증: `python -m unittest discover -s tests -v`

### 도구 실행 제한

로컬 MCP 도구는 호출마다 별도 Python 프로세스에서 실행하며, 시작·모듈 로딩·여러 HTTP 요청을
포함해 전체 120초를 넘기면 해당 프로세스와 자식 프로세스를 종료합니다. 각 호출의 프로세스
시작 비용이 추가됩니다. 수학 계산 30초와 파일 파싱 60초는 더 짧은 내부 제한으로 유지합니다.
에이전트는 종료 처리와 응답 전달 여유를 포함해 호출 전체를 최대 130초 기다립니다.
외부 `fetch` 서버에는 클라이언트 대기 제한이 적용되지만 외부 서버 작업 중단까지 보장하지는 않습니다.

MCP 연결·초기화는 서버마다 30초, 도구 목록 조회는 모든 페이지를 합해 30초로 제한합니다.
서버 간 중복 도구 이름은 오류로 처리합니다.
어떤 도구든 시간 초과가 발생하면 해당 질문에서는 새 도구 실행을 중지하고,
`recall_tool_result`로 이미 저장된 근거만 조회한 뒤 답합니다.
이메일처럼 외부에 영향을 주는 작업은 시간 초과 전에 이미 반영되었을 수도 있으므로
실패로 단정하거나 자동으로 재발송하지 않습니다.

모델/MCP 없이 회귀 테스트:
`python -m unittest discover -s tests -p "test_agent*.py" -v`
및 `python -m unittest discover -s tests -p test_tool_runtime.py -v`.

### 도구 추가

`my_server.py`에 `@mcp.tool()`을 붙인 함수를 추가하면 새 도구가 된다. 함수 설명(docstring)이 모델에게 전달된다.

```python
@mcp.tool()
def add(a: float, b: float) -> float:
    """두 수를 더한다."""
    return a + b
```

추가 후 `agent.py --tools`로 목록에 나오는지 확인.
다른 MCP 서버를 연결하려면 `agent.py`의 `SERVERS`에 등록한다.

> `mcp`는 2 미만으로 고정 — 공식 `mcp-server-fetch` 서버가 아직 mcp 2.0과 맞지 않음

## Documentation

| 문서 | 내용 |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | 프로젝트 계획 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 설계 (추가 예정) |
| [docs/meetings/](docs/meetings/) | 회의록 |
| [eval/README.md](eval/README.md) | 평가셋 형식 |

## Expected Output

> 추가 예정

## Evaluation Metrics

GAIA 벤치마크 방식(레벨 1~3, 정답 정규화 비교) + 과제 공지 예시의 형식 요구(출처·기준일·표)로 채점한다.

```bash
.venv/bin/python eval/run_eval.py --mode both   # Agent vs baseline(도구 없이 모델만)
```

| 지표 | 의미 |
|---|---|
| 정답률 (전체·레벨별) | 최종 답 일치 + 형식 요구 충족 |
| 형식 요구 충족률 | 출처·기준일·표 등 |
| 평균·총 소요 시간 | 동점 시 순위 기준 |
| 도구 호출·오류 수 | 도구 사용 효율 |

평가셋 구성·실행 옵션: [eval/README.md](eval/README.md)

## Known Issues / Operational Notes

### 모델 사용 규정

> 출처: eTL 공지 "Final project 로컬 모델 관련" (2026-11-12 확인)

- online model(ChatGPT, Claude 등) API 사용 **금지** — 전부 **로컬 모델**로 진행
- 모든 팀에 공통 제공되는 로컬 모델 **`Qwen3.8-27B`** 기준, 이보다 파라미터 사이즈가 큰 모델은 **사용 불가**
  - 최신 여부는 무관 (Qwen3.8-27B 이후에 나온 모델이라도 15B면 사용 가능)
- MoE 모델은 괄호 앞의 **큰 숫자**(전체 파라미터)가 기준
  - 예: `MiniMax-M3 427B (23B active)` → 427B 기준이므로 **사용 불가**
- 추가 문의: 조교 메일 (eTL 공지 참고)

### 과제 공지 사항
- TA가 각 팀 코드를 사전 설치해두고 실행 (환경설정 맞춤 허용)
- 각 팀은 "우리는 풀 수 있지만 다른 팀은 못 풀 것 같은 문제"를 하나씩 제출
- 테스트 문제는 제공됨
- 세부 사항은 변동될 수 있으며 조교가 계속 공지

