#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".md"}


def load_registry(path: Path) -> list[dict]:
    records = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def list_raw_files(knowledge_base: Path) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for file_path in sorted(knowledge_base.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        relative = file_path.relative_to(knowledge_base)
        top = relative.parts[0] if len(relative.parts) > 1 else "Root"
        grouped[top].append(str(relative).replace("\\", "/"))
    return grouped


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    references_root = skill_root / "references"
    knowledge_base = references_root / "knowledge_base"
    registry_path = references_root / "registry.jsonl"
    index_path = references_root / "knowledge_index.md"

    records = load_registry(registry_path)
    status_counter = Counter(record.get("status", "unknown") for record in records)
    type_counter = Counter(record.get("file_type", "unknown") for record in records)
    category_counter = Counter(record.get("business_category", "uncategorized") for record in records)
    grouped_files = list_raw_files(knowledge_base)

    lines = [
        "# Knowledge Index",
        "",
        "Base path: `references/knowledge_base`",
        "",
        "## Processed Snapshot",
        f"- Registry entries: `{len(records)}`",
        f"- Processed root: `references/processed`",
        f"- File types: `{dict(sorted(type_counter.items()))}`",
        f"- Business categories: `{dict(sorted(category_counter.items()))}`",
        f"- Status counts: `{dict(sorted(status_counter.items()))}`",
        "",
        "## Ingestion Workflow",
        "- New files should be ingested with `python3 scripts/ingest.py --source <path> --rebuild-index`.",
        "- Answers should use `references/processed/<doc_id>/chunks.jsonl` and `text.md` before reopening raw files.",
        "- When a PowerPoint is legacy `.ppt`, prefer a paired PDF if present.",
        "",
    ]

    for section_name, files in grouped_files.items():
        lines.append(f"## {section_name}")
        for entry in files:
            lines.append(f"- `references/knowledge_base/{entry}`")
        lines.append("")

    if records:
        lines.append("## Registry Entries")
        for record in sorted(records, key=lambda item: item["source_path"]):
            lines.append(
                "- `{source}` -> `{processed}` | type=`{file_type}` | category=`{category}` | status=`{status}`".format(
                    source=record["source_path"],
                    processed=record["processed_root"],
                    file_type=record["file_type"],
                    category=record["business_category"],
                    status=record["status"],
                )
            )
        lines.append("")

    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(index_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
