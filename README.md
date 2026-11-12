# [팀 이름] — QA AI Agent

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

> 추가 예정

- LLM: **로컬 모델만 사용** — 공통 제공 모델 `Qwen3.8-27B` 기준 (아래 [모델 사용 규정](#모델-사용-규정) 참고). 사용할 모델은 미정
- 초기 레포 템플릿은 Python 기준으로 만들어져 있음 (변경 가능)

## Repository Structure

> 현재 초기 템플릿 기준 — 구조 확정 시 갱신

```
.
├── agent/            # 에이전트 본체 (미구현)
│   └── main.py
├── tools/            # 도구 모음 — 파일 하나 = 도구 하나
│   ├── __init__.py   #   도구 자동 등록
│   ├── _template.py  #   도구 템플릿
│   └── today.py      #   예시 도구
├── eval/             # 평가 문제셋
├── docs/             # 계획, 회의록
├── .github/          # 이슈·PR 템플릿
├── requirements.txt
└── .env.example
```

## Development Roadmap

| 기간 | 내용 |
|---|---|
| 11/12 ~ 다음 주 | 도구 아이디어 공유 → 도구 만들기 → 모아서 연결하기 |
| 그 다음 주 | 성능 평가 지표 만들기 → 에이전트 성능 평가 → 완성 |
| **11/25 (수) 자정** | **팀별 코드 제출** |
| ~11/30 (월) | 연구실 방문해 실제 미션 수행 |
| 12/2 (수) | 결과 발표 (팀별 10분) |

## Installation and Usage

> 추가 예정

현재 템플릿에서 동작하는 명령:

```bash
pip install -r requirements.txt
python -m agent.main --list-tools   # 등록된 도구 확인
python -m tools.today               # 도구 단독 테스트
```

## Documentation

| 문서 | 내용 |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | 프로젝트 계획 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 설계 (추가 예정) |
| [docs/meetings/](docs/meetings/) | 회의록 |
| [tools/README.md](tools/README.md) | 도구 추가 방법 |
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

