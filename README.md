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
ollama pull qwen3-vl:2b-instruct
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
ollama pull qwen3-vl:2b-instruct
```

### 실행

macOS / Linux는 `.venv/bin/python`, Windows는 `.\.venv\Scripts\python.exe`

```bash
.venv/bin/python agent.py --tools                                  # 연결된 도구 목록
.venv/bin/python agent.py "위키백과에서 서울대학교를 찾아서 두 문장으로 알려줘"   # 질문하기
```

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

> 추가 예정 (다음 다음 주 확정)

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

