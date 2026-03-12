#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List


WORD_RE = re.compile(r"[A-Za-z0-9_]+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

QUERY_CATEGORY_HINTS = {
    "finished_inspection_process": ["成品查貨流程", "成品查货流程", "尾期查货", "3.3a", "3.3b"],
    "semi_finished_inspection_process": ["半成品查貨流程", "半成品查货流程", "半成品查货", "4.7"],
    "quality_standard": ["品質標準", "品质标准", "aql", "允差", "抽样标准", "抽樣標準"],
    "defect_catalog": ["疵點", "疵点", "缺陷", "打褶问题", "破洞", "污渍", "污漬", "色差"],
    "inspection_guideline": ["产品检查及查货工作指引", "產品檢查及查貨工作指引"],
    "work_guideline": ["品質保證部工作指引", "品质保证部工作指引"],
    "inspection_plan": ["订单查货计划", "訂單查貨計劃", "inspection plan"],
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def tokenize(text: str) -> List[str]:
    text = normalize(text)
    latin_tokens = WORD_RE.findall(text)
    cjk_chars = CJK_RE.findall(text)
    cjk_bigrams = ["".join(cjk_chars[index : index + 2]) for index in range(len(cjk_chars) - 1)]
    return latin_tokens + cjk_chars + cjk_bigrams


def load_registry(path: Path) -> Dict[str, Dict]:
    records: Dict[str, Dict] = {}
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                record = json.loads(line)
                records[record["doc_id"]] = record
    return records


def iter_chunks(processed_root: Path) -> Iterable[Dict]:
    for chunk_file in sorted(processed_root.glob("*/chunks.jsonl")):
        with chunk_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)


def score_text(query_tokens: Counter, text: str, weight: float) -> float:
    if not text:
        return 0.0
    tokens = Counter(tokenize(text))
    score = 0.0
    for token, count in query_tokens.items():
        if token in tokens:
            score += min(count, tokens[token]) * weight
    return score


def score_chunk(query: str, query_tokens: Counter, chunk: Dict) -> float:
    score = 0.0
    score += score_text(query_tokens, chunk.get("heading", ""), 4.0)
    score += score_text(query_tokens, chunk.get("source_path", ""), 2.5)
    score += score_text(query_tokens, chunk.get("text", ""), 1.0)

    query_norm = normalize(query)
    text_norm = normalize(chunk.get("text", ""))
    heading_norm = normalize(chunk.get("heading", ""))
    if query_norm and query_norm in text_norm:
        score += 6.0
    if query_norm and query_norm in heading_norm:
        score += 8.0

    query_terms = [token for token in tokenize(query) if len(token) > 1]
    if query_terms:
        matched_terms = sum(1 for token in query_terms if token in tokenize(chunk.get("text", "")))
        coverage = matched_terms / len(query_terms)
        score += coverage * 4.0

    location_value = str(chunk.get("location_value", ""))
    if location_value and query_norm and query_norm in normalize(location_value):
        score += 2.0

    return score


def detect_query_category(query: str) -> str | None:
    lowered = normalize(query)
    best_category = None
    best_score = 0
    for category, hints in QUERY_CATEGORY_HINTS.items():
        score = sum(1 for hint in hints if hint.lower() in lowered)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def make_preview(text: str, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def search(
    query: str,
    registry: Dict[str, Dict],
    processed_root: Path,
    top_k: int,
    business_category: str | None,
    file_type: str | None,
) -> List[Dict]:
    query_tokens = Counter(tokenize(query))
    query_category = detect_query_category(query)
    if not query_tokens:
        return []

    results: List[Dict] = []
    for chunk in iter_chunks(processed_root):
        record = registry.get(chunk["doc_id"])
        if not record:
            continue
        if business_category and record.get("business_category") != business_category:
            continue
        if file_type and record.get("file_type") != file_type:
            continue

        score = score_chunk(query, query_tokens, chunk)
        if query_category:
            if record.get("business_category") == query_category:
                score += 10.0
            else:
                score -= 2.0
        if score <= 0:
            continue

        results.append(
            {
                "score": round(score, 4),
                "doc_id": chunk["doc_id"],
                "source_path": chunk["source_path"],
                "business_category": record.get("business_category"),
                "file_type": record.get("file_type"),
                "location_label": chunk.get("location_label"),
                "location_value": chunk.get("location_value"),
                "heading": chunk.get("heading"),
                "preview": make_preview(chunk.get("text", "")),
            }
        )

    results.sort(
        key=lambda item: (
            item["score"],
            -len(item["preview"]),
            item["source_path"],
        ),
        reverse=True,
    )
    return results[:top_k]


def render_text(results: List[Dict]) -> str:
    if not results:
        return "No matches."
    lines = []
    for index, item in enumerate(results, start=1):
        lines.extend(
            [
                f"{index}. score={item['score']}",
                f"   source={item['source_path']}",
                f"   type={item['file_type']} category={item['business_category']}",
                f"   location={item['location_label']}:{item['location_value']}",
                f"   heading={item['heading']}",
                f"   preview={item['preview']}",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve relevant processed chunks for QA.")
    parser.add_argument("--query", required=True, help="User question or retrieval query.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of top chunks to return.")
    parser.add_argument("--category", default=None, help="Optional business category filter.")
    parser.add_argument("--file-type", default=None, help="Optional file type filter.")
    parser.add_argument("--json", action="store_true", help="Print JSON results.")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    registry = load_registry(skill_root / "references" / "registry.jsonl")
    results = search(
        query=args.query,
        registry=registry,
        processed_root=skill_root / "references" / "processed",
        top_k=args.top_k,
        business_category=args.category,
        file_type=args.file_type,
    )

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render_text(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
