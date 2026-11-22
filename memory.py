import json
import math
import uuid
from datetime import datetime
from pathlib import Path

import ollama


BASE_DIR = Path(__file__).resolve().parent / "memory"
RECORDS_DIR = BASE_DIR / "records"
INDEX_FILE = BASE_DIR / "index.json"
EMBED_MODEL = "bge-m3"

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
TOP_K = 4
MIN_SCORE = 0.20


def _embed(texts: list[str]) -> list[list[float]]:
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return [list(vector) for vector in response.embeddings]


def _chunks(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    result = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        result.append(text[start:end])
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP

    return result


def _load_index() -> list[dict]:
    if not INDEX_FILE.exists():
        return []

    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        if data.get("model") != EMBED_MODEL:
            return []
        return data.get("chunks", [])
    except (OSError, json.JSONDecodeError):
        return []


def _save_index(chunks: list[dict]) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"model": EMBED_MODEL, "chunks": chunks}
    temp_file = INDEX_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )
    temp_file.replace(INDEX_FILE)


def save_qa(question: str, answer: str) -> str:
    """질문과 답변을 날짜별 텍스트 파일로 저장하고 임베딩 색인에 추가한다."""
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone()
    filename = f"{now:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.txt"
    record_path = RECORDS_DIR / filename

    content = (
        f"날짜: {now:%Y-%m-%d %H:%M:%S %Z}\n\n"
        f"질문:\n{question.strip()}\n\n"
        f"답변:\n{answer.strip()}\n"
    )

    # 임베딩 생성에 실패해도 텍스트 원본은 남도록 먼저 저장
    record_path.write_text(content, encoding="utf-8")

    text_chunks = _chunks(content)
    vectors = _embed(text_chunks)

    index = _load_index()
    for i, (chunk, vector) in enumerate(zip(text_chunks, vectors)):
        index.append({
            "file": filename,
            "part": i,
            "text": chunk,
            "embedding": vector,
        })

    _save_index(index)
    return filename


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_memories(query: str) -> str:
    """질문과 의미가 가까운 과거 대화 조각을 최대 TOP_K개 검색한다."""
    index = _load_index()
    if not index:
        return ""

    query_vector = _embed([query])[0]
    scored = []

    for item in index:
        if not (RECORDS_DIR / item["file"]).exists():
            continue
        score = _cosine_similarity(query_vector, item["embedding"])
        if score >= MIN_SCORE:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    # 같은 파일에서 여러 조각이 뽑히면 가장 관련 높은 조각 하나만 사용
    selected = []
    seen_files = set()
    for score, item in scored:
        if item["file"] in seen_files:
            continue
        seen_files.add(item["file"])
        selected.append((score, item))
        if len(selected) >= TOP_K:
            break

    return "\n\n".join(
        f"[기록: {item['file']} | 관련도 {score:.2f}]\n{item['text']}"
        for score, item in selected
    )