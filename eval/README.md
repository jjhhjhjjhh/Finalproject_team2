# 평가셋

GAIA(General AI Assistants 벤치마크) 방식 + 과제 공지 예시의 형식 요구를 합쳐 만든 평가셋.

- **GAIA에서 가져온 것**: 정답이 짧고 하나로 정해지는 문제, 레벨 1~3 난이도 구분, 정규화 후 정답 비교(quasi exact match), 웹 검색·계산·파일 읽기를 섞은 문제
- **과제 공지에서 가져온 것**: 예시 3문제(`ex1`~`ex3`) 그대로, 출처·기준일·표 같은 형식 요구(rubric)

## 문제 구성 (`questions.jsonl`, 14문제)

| 레벨 | 기준 | 문제 |
|---|---|---|
| L1 | 도구 0~1개, 짧은 단계 | ex1 삼단논법, g01 소수 합, g02 거듭제곱 나머지, g03 서울대 개교 연도, g04 CSV 합계, g05 PDF 읽기 |
| L2 | 도구 여러 개 조합 | ex2 2026 노벨 물리학상, g06 복리 + 표, g07 XLSX 조건 평균, g08·g09·g10 검색 + 계산 |
| L3 | 긴 계획, 여러 검색 + 비교 + 형식 요구 | ex3 국고채 복리, g11 노벨상 수상자 최고령 |

첨부 파일은 `files/`에 있고, 실행 시 `read_document`가 읽는 `documents/` 폴더로 자동 복사된다.

| 필드 | 설명 |
|---|---|
| `id` | `ex*` 과제 예시, `g*` 팀 작성 |
| `level` | GAIA 난이도 1~3 |
| `type` | `reasoning` `calc` `search` `file` `data_calc` |
| `question` | 문제 원문 |
| `final_answer` | 정답. 허용 답이 여러 개면 리스트. 최신 정보라 바뀌는 문제는 빈칸 |
| `answer_type` | `number`(쉼표·단위 떼고 값 비교) / `string`(공백·문장부호 떼고 비교) |
| `rubric` | 답에 꼭 들어가야 할 요소 — `label`, `pattern`(정규식) |
| `file` | 첨부 파일 이름 (`files/`) |
| `source` | 문제 출처 |

## 실행

프로젝트 루트에서:

```bash
python eval/run_eval.py               # Agent (도구 사용)
python eval/run_eval.py --mode both   # Agent vs baseline (도구 없이 모델만)
python eval/run_eval.py --level 1     # 레벨별
python eval/run_eval.py --ids ex1,g07 # 일부 문제만
python eval/run_eval.py --raw         # '최종 답:' 형식 안내 없이 원문 그대로
```

GAIA처럼 질문 끝에 "마지막 줄에 '최종 답: <답>'을 쓰라"는 안내를 붙여 그 줄로 채점한다.
그 줄이 없으면 답변의 마지막 줄로 채점한다. 평가 중에는 과거 대화 메모리를 끈다.

## 성능 평가 지표

| 지표 | 계산 |
|---|---|
| **정답률** (주 지표) | 최종 답 일치 AND rubric 전부 충족한 문제 비율 — 전체·레벨별 |
| 사람 확인 필요 | `final_answer`가 빈 문제(ex2·ex3) 중 rubric을 채운 것 → CSV `manual` 열에 O/X |
| 형식 요구 충족률 | rubric 항목(출처·기준일·표 등) 중 충족한 비율 |
| '최종 답' 형식 준수율 | 안내한 형식대로 답한 비율 |
| 평균·총 소요 시간 | 동점이면 더 빨리 푼 팀이 이기므로 함께 기록 |
| 도구 호출·오류 수 | 불필요한 호출, 자주 실패하는 도구 파악 |

baseline(도구 없음)과 Agent의 정답률 차이가 "도구를 붙여서 얼마나 좋아졌나"를 보여 준다.
결과는 `results/<시각>_<mode>.jsonl`, `.csv`에 저장된다.

## 문제 추가 시

- 정답이 하나로 정해지고 시간이 지나도 안 바뀌는 문제를 우선 (GAIA 원칙)
- 숫자 답은 `answer_type: number`, 표현이 여러 개인 답은 `final_answer`를 리스트로
- 출처·표 같은 형식 요구가 있으면 `rubric`에 정규식으로
