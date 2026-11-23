"""평가셋을 Agent에 일괄 실행하고 GAIA 방식으로 채점한다.

사용법 (프로젝트 루트에서)
  python eval/run_eval.py                    도구 사용 Agent로 전체 실행
  python eval/run_eval.py --mode both        Agent + baseline(도구 없이 모델만) 비교
  python eval/run_eval.py --ids ex1,g07      일부 문제만
  python eval/run_eval.py --level 1          레벨별 실행
  python eval/run_eval.py --raw              '최종 답:' 형식 안내 없이 원문 그대로 질문

채점
  - 정답(final_answer): GAIA의 quasi exact match — 숫자는 쉼표·단위를 떼고 값 비교, 문자열은 공백·문장부호를 떼고 비교
  - 형식 요구(rubric): 과제 공지 예시처럼 출처 URL·기준일·표 등 답에 꼭 들어가야 할 요소를 정규식으로 확인
  - 정답 = 최종 답 일치 AND rubric 전부 충족. final_answer가 빈 문제(최신 정보)는 rubric만 자동 확인하고 값은 사람이 확인
결과: eval/results/<시각>_<mode>.jsonl, .csv (manual 열에 사람이 O/X)
평가 중에는 과거 대화 메모리를 끈다.
"""
import argparse
import asyncio
import csv
import io
import json
import re
import shutil
import sys
import time
from collections import defaultdict
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
sys.path.insert(0, str(ROOT))

from agent import MODEL, ask  # noqa: E402

QUESTIONS = EVAL_DIR / "questions.jsonl"
FILES_DIR = EVAL_DIR / "files"
DOCUMENT_DIR = ROOT / "documents"  # my_server.read_document가 읽는 폴더
RESULTS_DIR = EVAL_DIR / "results"
FORMAT_SUFFIX = "\n\n답변의 마지막 줄에는 '최종 답: <답>' 형식으로 최종 답만 쓰시오."


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


# ---------- GAIA식 정규화·비교 ----------
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def to_number(text):
    match = NUMBER.search(text.replace(",", ""))
    return float(match.group()) if match else None


def normalize_text(text):
    return re.sub(r"[\s\W_]+", "", text).casefold()


def extract_final(answer):
    """'최종 답: ...' 줄을 찾는다. 없으면 None."""
    matches = re.findall(r"최종\s*답\s*[:：]\s*(.+)", answer or "")
    return matches[-1].strip().strip("*` ") if matches else None


def match_final(target, answer_type, final, full_answer):
    """최종 답 줄이 있으면 그것으로, 없으면 답변 전체에서 찾는다."""
    targets = target if isinstance(target, list) else [target]
    if answer_type == "number":
        candidates = [to_number(final)] if final else [
            float(n) for n in NUMBER.findall((full_answer or "").replace(",", ""))
        ]
        return any(
            c is not None and abs(c - float(t)) < 1e-6 for c in candidates for t in targets
        )
    haystack = normalize_text(final if final else full_answer or "")
    return any(normalize_text(t) in haystack for t in targets)


def grade(item, answer):
    final = extract_final(answer)
    rubric = {r["label"]: bool(re.search(r["pattern"], answer or "")) for r in item.get("rubric", [])}
    target = item.get("final_answer")
    final_ok = match_final(target, item.get("answer_type", "string"), final, answer) if target else None
    if not answer:
        status = "fail"
    elif final_ok is None:
        status = "check" if all(rubric.values()) else "fail"  # 값은 사람이 확인
    else:
        status = "pass" if final_ok and all(rubric.values()) else "fail"
    return {
        "status": status,
        "final_extracted": final or "",
        "format_ok": final is not None,
        "final_ok": final_ok,
        "rubric": rubric,
    }


# ---------- 실행 ----------
def load_questions(ids=None, level=None):
    items = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    if ids:
        items = [item for item in items if item["id"] in set(ids)]
    if level:
        items = [item for item in items if item["level"] == level]
    return items


def prepare_files(items):
    """첨부 파일을 read_document가 읽는 documents/ 폴더에 복사한다."""
    for item in items:
        if item.get("file"):
            DOCUMENT_DIR.mkdir(exist_ok=True)
            shutil.copy2(FILES_DIR / item["file"], DOCUMENT_DIR / item["file"])


async def run_one(item, use_tools, raw):
    question = item["question"] if raw else item["question"] + FORMAT_SUFFIX
    log = io.StringIO()
    start = time.perf_counter()
    error = ""
    try:
        with redirect_stdout(Tee(sys.stdout, log)):
            answer = await ask(question, use_tools=use_tools, use_memory=False)
    except Exception as exc:  # 한 문제가 실패해도 계속
        answer, error = None, f"{type(exc).__name__}: {exc}"
    output = log.getvalue()
    return {
        "id": item["id"],
        "level": item["level"],
        "type": item.get("type", ""),
        "mode": "agent" if use_tools else "baseline",
        "seconds": round(time.perf_counter() - start, 1),
        **grade(item, answer),
        "expected": item.get("final_answer", ""),
        "tool_calls": len(re.findall(r"^\[TOOL CALL\]", output, re.M)),
        "tool_errors": len(re.findall(r"^\[TOOL RESULT\] (?:도구 실행 오류|오류:|웹 검색 오류)", output, re.M)),
        "model_turns": len(re.findall(r"^\[MODEL\] .*응답 대기 중", output, re.M)),
        "error": error,
        "answer": answer or "",
    }


def summarize(rows):
    def rate(part, whole):
        return f"{part}/{whole}" + (f" ({part / whole:.0%})" if whole else "")

    auto = [r for r in rows if r["final_ok"] is not None]
    rubric_items = [ok for r in rows for ok in r["rubric"].values()]
    lines = [
        f"정답률(자동 채점) {rate(sum(r['status'] == 'pass' for r in auto), len(auto))}",
        f"사람 확인 필요 {sum(r['status'] == 'check' for r in rows)}",
        f"형식 요구 충족 {rate(sum(rubric_items), len(rubric_items))}",
        f"'최종 답' 형식 준수 {rate(sum(r['format_ok'] for r in rows), len(rows))}",
        f"평균 {sum(r['seconds'] for r in rows) / len(rows):.1f}초 · 총 {sum(r['seconds'] for r in rows):.1f}초",
        f"도구 호출 {sum(r['tool_calls'] for r in rows)} · 도구 오류 {sum(r['tool_errors'] for r in rows)}",
    ]
    by_level = defaultdict(list)
    for r in auto:
        by_level[r["level"]].append(r["status"] == "pass")
    lines.append("레벨별 " + " · ".join(
        f"L{level} {rate(sum(v), len(v))}" for level, v in sorted(by_level.items())
    ))
    return lines


def save(rows, mode):
    RESULTS_DIR.mkdir(exist_ok=True)
    stem = RESULTS_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{mode}"
    with open(stem.with_suffix(".jsonl"), "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps({**row, "model": MODEL}, ensure_ascii=False) + "\n")
    fields = ["id", "level", "type", "mode", "status", "expected", "final_extracted", "final_ok",
              "rubric", "seconds", "tool_calls", "tool_errors", "model_turns", "error", "answer", "manual"]
    with open(stem.with_suffix(".csv"), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            rubric = " ".join(f"{k}:{'O' if v else 'X'}" for k, v in row["rubric"].items())
            expected = row["expected"]
            writer.writerow({**row, "rubric": rubric, "manual": "",
                             "expected": " / ".join(expected) if isinstance(expected, list) else expected})
    return stem


async def main():
    parser = argparse.ArgumentParser(description="QA Agent 평가 (GAIA 방식)")
    parser.add_argument("--mode", choices=["agent", "baseline", "both"], default="agent")
    parser.add_argument("--ids", help="쉼표로 구분한 문제 ID (예: ex1,g07)")
    parser.add_argument("--level", type=int, choices=[1, 2, 3])
    parser.add_argument("--raw", action="store_true", help="'최종 답:' 형식 안내 없이 질문")
    args = parser.parse_args()

    items = load_questions(args.ids.split(",") if args.ids else None, args.level)
    if not items:
        sys.exit("[ERROR] 실행할 문제가 없습니다.")
    prepare_files(items)

    summaries = {}
    for use_tools in {"agent": [True], "baseline": [False], "both": [True, False]}[args.mode]:
        mode = "agent" if use_tools else "baseline"
        rows = []
        for number, item in enumerate(items, start=1):
            print(f"\n===== [{mode}] {number}/{len(items)} {item['id']} (L{item['level']}) =====", flush=True)
            rows.append(await run_one(item, use_tools, args.raw))
        path = save(rows, mode)
        summaries[mode] = summarize(rows)
        print(f"\n[EVAL] 결과 저장: {path.relative_to(ROOT)}.jsonl / .csv")

    print(f"\n===== 요약 (모델: {MODEL}) =====")
    for mode, lines in summaries.items():
        print(f"[{mode}]\n  " + "\n  ".join(lines))
    print("※ status가 check인 문제(최신 정보)는 CSV에서 값을 직접 확인해 manual 열에 O/X를 적으세요.")


if __name__ == "__main__":
    asyncio.run(main())
