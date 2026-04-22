#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from zipfile import ZipFile

try:
    from docx import Document
    from docx.oxml.ns import qn
except Exception:
    Document = None
    qn = None


SUPPORTED_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".md"}
IGNORED_PREFIXES = ("~$", ".")
RAW_SOURCES_DIR = "references/raw/sources"
RAW_MANIFEST_PATH = "references/raw/source_manifest.json"
RAW_INDEX_PATH = "references/raw/source_index.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_ingest_module(skill_root: Path):
    module_path = skill_root / "scripts" / "ingest.py"
    spec = importlib.util.spec_from_file_location("skill_ingest", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_manifest(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sources", {})


def load_registry(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def registry_maps(records: List[Dict[str, Any]]) -> tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    by_source_path = {record["source_path"]: record for record in records}
    by_origin_path: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        origin = record.get("origin_path")
        if not origin:
            continue
        by_origin_path.setdefault(origin, []).append(record)
    return by_source_path, by_origin_path


def is_supported_raw_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and not path.name.startswith(IGNORED_PREFIXES)
    )


def discover_source_dirs(raw_root: Path) -> Iterable[Path]:
    if not raw_root.exists():
        return []
    return [path for path in sorted(raw_root.iterdir()) if path.is_dir() and not path.name.startswith(IGNORED_PREFIXES)]


def list_source_files(source_dir: Path) -> List[Path]:
    return [path for path in sorted(source_dir.iterdir()) if is_supported_raw_file(path)]


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def markdown_cell(text: str) -> str:
    return clean_text(text).replace("|", "\\|").replace("\n", "<br>")


def markdown_table(table) -> str:
    rows: List[List[str]] = []
    for row in table.rows:
        values = [markdown_cell(cell.text) for cell in row.cells]
        if any(value.strip() for value in values):
            rows.append(values)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(padded[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in padded[1:] or [[""] * width]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def normalize_defect_name(name: str) -> str:
    normalized = name.strip()
    normalized = re.sub(r"（[^）]*）", "", normalized)
    normalized = re.sub(r"\([^)]*\)", "", normalized)
    return normalized.strip()


def make_safe_slug(name: str) -> str:
    slug = name.replace("/", "-")
    slug = re.sub(r"[\\:*?\"<>|]+", "-", slug)
    slug = re.sub(r"\s+", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def parse_defect_docx_sections(docx_path: Path) -> List[Dict[str, Any]]:
    if Document is None or qn is None:
        raise RuntimeError("python-docx is not available.")

    document = Document(str(docx_path))
    rels = document.part.rels
    body = document.element.body
    namespaces = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    sections: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    mode: str | None = None
    table_index = 0

    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            texts = [node.text for node in child.iter(qn("w:t")) if node.text]
            text = "".join(texts).strip()
            embeds: List[str] = []
            for blip in child.findall(".//a:blip", namespaces):
                rel_id = blip.get(qn("r:embed"))
                if rel_id and rel_id in rels:
                    embeds.append(Path(str(rels[rel_id].target_part.partname)).name)

            heading_match = re.match(r"^(\d+)、(.+)$", text)
            if heading_match:
                current = {
                    "index": int(heading_match.group(1)),
                    "raw_heading": text,
                    "name": normalize_defect_name(heading_match.group(2)),
                    "images": [],
                    "table": None,
                }
                sections.append(current)
                mode = None
                continue

            if re.match(r"^\d+\.1疵點圖片$", text):
                mode = "images"
                continue

            if re.match(r"^\d+\.2問題原因及解決方案$", text):
                mode = "table"
                continue

            if embeds and current is not None and mode == "images":
                current["images"].extend(embeds)

        elif tag == "tbl":
            table = document.tables[table_index]
            table_index += 1
            if current is not None and mode == "table" and current.get("table") is None:
                current["table"] = table

    return sections


def build_defect_catalog_plan(skill_root: Path, source_dir_rel: str, config: Dict[str, Any]) -> Dict[str, Any]:
    source_dir = skill_root / RAW_SOURCES_DIR / source_dir_rel
    source_file = config.get("source_file")
    if source_file:
        docx_path = source_dir / source_file
    else:
        candidates = [path for path in list_source_files(source_dir) if path.suffix.lower() == ".docx"]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one .docx in {source_dir_rel}, found {len(candidates)}.")
        docx_path = candidates[0]

    sections = parse_defect_docx_sections(docx_path)
    slug_overrides = config.get("slug_overrides", {})
    subcategory = config["target_subcategory"]
    target_root_rel = f"references/knowledge_base/Defect Analysis Table/{subcategory}"

    planned_sections: List[Dict[str, Any]] = []
    for section in sections:
        raw_name = section["name"]
        slug = slug_overrides.get(raw_name, make_safe_slug(raw_name))
        folder_name = f"{section['index']}-{slug}"
        folder_rel = f"{target_root_rel}/{folder_name}"
        md_rel = f"{folder_rel}/{folder_name}.md"
        image_paths = []
        for image_index, image_name in enumerate(section["images"], start=1):
            ext = Path(image_name).suffix.lower()
            image_paths.append(
                {
                    "source_name": image_name,
                    "dest_rel": f"{folder_rel}/images/media/image{image_index}{ext}",
                    "markdown_rel": f"images/media/image{image_index}{ext}",
                }
            )

        if "（" in section["raw_heading"] or "(" in section["raw_heading"]:
            heading_text = section["raw_heading"]
        else:
            heading_text = f"{section['index']}、{raw_name}（{subcategory}）"

        planned_sections.append(
            {
                "index": section["index"],
                "raw_name": raw_name,
                "slug": slug,
                "folder_rel": folder_rel,
                "md_rel": md_rel,
                "heading_text": heading_text,
                "table_md": markdown_table(section["table"]) if section.get("table") is not None else "",
                "images": image_paths,
            }
        )

    return {
        "mode": "defect_catalog_docx_split",
        "source_dir_rel": f"{RAW_SOURCES_DIR}/{source_dir_rel}",
        "source_file_rel": str(docx_path.relative_to(skill_root)).replace("\\", "/"),
        "subcategory": subcategory,
        "target_root_rel": target_root_rel,
        "target_data_structure_rel": f"{target_root_rel}/data_structure.md",
        "sections": planned_sections,
    }


def write_defect_catalog_outputs(skill_root: Path, plan: Dict[str, Any]) -> List[str]:
    updated_paths: List[str] = []
    source_docx = skill_root / plan["source_file_rel"]
    target_root = skill_root / plan["target_root_rel"]
    ensure_directory(target_root)

    with ZipFile(source_docx) as archive:
        for section in plan["sections"]:
            folder = skill_root / section["folder_rel"]
            images_dir = folder / "images" / "media"
            ensure_directory(images_dir)

            image_markdown = []
            for image in section["images"]:
                destination = skill_root / image["dest_rel"]
                ensure_directory(destination.parent)
                with archive.open(f"word/media/{image['source_name']}") as src, destination.open("wb") as dst:
                    dst.write(src.read())
                image_markdown.append(f"![]({image['markdown_rel']})")
                updated_paths.append(image["dest_rel"])

            body = "\n\n".join(
                [
                    f"**{section['heading_text']}**",
                    f"{section['index']}.1疵點圖片",
                    " ".join(image_markdown) if image_markdown else "暂无图片",
                    f"{section['index']}.2問題原因及解決方案",
                    section["table_md"],
                ]
            ).rstrip() + "\n"
            md_path = skill_root / section["md_rel"]
            md_path.write_text(body, encoding="utf-8")
            updated_paths.append(section["md_rel"])

    lines = [f"# 知识分类目录: {plan['subcategory']}", "", f"本目录放置{plan['subcategory']}以下情况:", ""]
    for section in plan["sections"]:
        folder_name = Path(section["folder_rel"]).name
        file_name = Path(section["md_rel"]).name
        lines.append(f"- {folder_name}")
        lines.append(
            f"  - 该目录放置了{plan['subcategory']}有关{section['raw_name']}的问题种类，问题发生阶段，问题类型，问题原因，问题说明，解决方法，预防措施。"
        )
        lines.append(f"  - 详细可参考文件 [{file_name}]({folder_name}/{file_name})")
        lines.append("")
    data_structure = skill_root / plan["target_data_structure_rel"]
    data_structure.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    updated_paths.append(plan["target_data_structure_rel"])
    return updated_paths


def check_registry_targets(
    skill_root: Path,
    target_paths: List[str],
    by_source_path: Dict[str, Dict[str, Any]],
) -> tuple[List[str], List[str], List[str]]:
    missing_files: List[str] = []
    missing_registry: List[str] = []
    missing_processed: List[str] = []

    for target in target_paths:
        if not (skill_root / target).exists():
            missing_files.append(target)
            continue
        record = by_source_path.get(target)
        if not record:
            missing_registry.append(target)
            continue
        processed_root = record.get("processed_root")
        if not processed_root or not (skill_root / processed_root).exists():
            missing_processed.append(target)
    return missing_files, missing_registry, missing_processed


def check_linked_existing(
    skill_root: Path,
    source_dir_rel: str,
    config: Dict[str, Any],
    by_source_path: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    targets = config.get("linked_targets", [])
    missing_files, missing_registry, missing_processed = check_registry_targets(skill_root, targets, by_source_path)
    status = "ok" if not (missing_files or missing_registry or missing_processed) else "missing_outputs"
    return {
        "status": status,
        "mode": "linked_existing",
        "source_dir": f"{RAW_SOURCES_DIR}/{source_dir_rel}",
        "raw_files": [
            str(path.relative_to(skill_root)).replace("\\", "/")
            for path in list_source_files(skill_root / RAW_SOURCES_DIR / source_dir_rel)
        ],
        "expected_targets": targets,
        "missing_files": missing_files,
        "missing_registry": missing_registry,
        "missing_processed": missing_processed,
    }


def check_direct_ingest(
    skill_root: Path,
    source_dir_rel: str,
    by_origin_path: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    source_dir = skill_root / RAW_SOURCES_DIR / source_dir_rel
    raw_files = [
        str(path.relative_to(skill_root)).replace("\\", "/")
        for path in list_source_files(source_dir)
    ]
    pending: List[str] = []
    processed_roots: List[str] = []
    for raw_file in raw_files:
        matches = by_origin_path.get(raw_file, [])
        if not matches:
            pending.append(raw_file)
            continue
        for match in matches:
            processed_roots.append(match.get("processed_root", ""))

    status = "ok" if raw_files and not pending else "pending_ingest"
    return {
        "status": status,
        "mode": "direct_ingest",
        "source_dir": f"{RAW_SOURCES_DIR}/{source_dir_rel}",
        "raw_files": raw_files,
        "pending_origin_links": pending,
        "processed_roots": [root for root in processed_roots if root],
    }


def check_defect_catalog(
    skill_root: Path,
    source_dir_rel: str,
    config: Dict[str, Any],
    by_source_path: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    plan = build_defect_catalog_plan(skill_root, source_dir_rel, config)
    expected_targets = [plan["target_data_structure_rel"]] + [section["md_rel"] for section in plan["sections"]]
    expected_assets = [image["dest_rel"] for section in plan["sections"] for image in section["images"]]

    missing_files, missing_registry, missing_processed = check_registry_targets(skill_root, expected_targets, by_source_path)
    missing_assets = [asset for asset in expected_assets if not (skill_root / asset).exists()]
    status = "ok" if not (missing_files or missing_registry or missing_processed or missing_assets) else "missing_outputs"

    return {
        "status": status,
        "mode": "defect_catalog_docx_split",
        "source_dir": plan["source_dir_rel"],
        "raw_files": [plan["source_file_rel"]],
        "target_root": plan["target_root_rel"],
        "expected_targets": expected_targets,
        "missing_files": missing_files,
        "missing_registry": missing_registry,
        "missing_processed": missing_processed,
        "missing_assets": missing_assets,
        "section_count": len(plan["sections"]),
    }


def apply_direct_ingest(skill_root: Path, source_dir_rel: str, force: bool) -> int:
    ingest = load_ingest_module(skill_root)
    source_dir = skill_root / RAW_SOURCES_DIR / source_dir_rel
    processed = 0
    for raw_file in list_source_files(source_dir):
        ingest.ingest_path(skill_root, raw_file, force=force)
        processed += 1
    return processed


def apply_defect_catalog(skill_root: Path, source_dir_rel: str, config: Dict[str, Any], force: bool) -> Dict[str, Any]:
    plan = build_defect_catalog_plan(skill_root, source_dir_rel, config)
    updated_paths = write_defect_catalog_outputs(skill_root, plan)
    ingest = load_ingest_module(skill_root)
    ingest.ingest_path(skill_root, skill_root / plan["target_root_rel"], force=force)
    return {
        "updated_paths": updated_paths,
        "target_root": plan["target_root_rel"],
        "section_count": len(plan["sections"]),
    }


def build_source_entry(
    skill_root: Path,
    source_dir_rel: str,
    config: Dict[str, Any],
    by_source_path: Dict[str, Dict[str, Any]],
    by_origin_path: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    mode = config.get("mode", "direct_ingest")
    if mode == "linked_existing":
        return check_linked_existing(skill_root, source_dir_rel, config, by_source_path)
    if mode == "defect_catalog_docx_split":
        return check_defect_catalog(skill_root, source_dir_rel, config, by_source_path)
    return check_direct_ingest(skill_root, source_dir_rel, by_origin_path)


def write_source_index(path: Path, entries: List[Dict[str, Any]]) -> None:
    ensure_directory(path.parent)
    summary: Dict[str, int] = {}
    for entry in entries:
        summary[entry["status"]] = summary.get(entry["status"], 0) + 1
    payload = {
        "generated_at": utc_now_iso(),
        "entries": entries,
        "status_counts": dict(sorted(summary.items())),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and sync retained raw source files into the knowledge base.")
    parser.add_argument("--apply", action="store_true", help="Apply processing rules for raw sources.")
    parser.add_argument("--force", action="store_true", help="Rebuild outputs even if they already exist.")
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Optional raw source directory name under references/raw/sources. Repeat to limit processing.",
    )
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild knowledge_index.md after apply.")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    raw_root = skill_root / RAW_SOURCES_DIR
    manifest = load_manifest(skill_root / RAW_MANIFEST_PATH)
    selected_sources = set(args.source or [])

    if args.apply:
        applied_summary: List[Dict[str, Any]] = []
        for source_dir in discover_source_dirs(raw_root):
            if selected_sources and source_dir.name not in selected_sources:
                continue
            config = manifest.get(source_dir.name, {})
            mode = config.get("mode", "direct_ingest")
            if mode == "linked_existing":
                continue
            if mode == "defect_catalog_docx_split":
                result = apply_defect_catalog(skill_root, source_dir.name, config, force=args.force)
                applied_summary.append({"source": source_dir.name, "mode": mode, **result})
                continue
            processed = apply_direct_ingest(skill_root, source_dir.name, force=args.force)
            applied_summary.append({"source": source_dir.name, "mode": "direct_ingest", "processed_files": processed})

        if args.rebuild_index:
            subprocess.run(["python3", str(skill_root / "scripts" / "build_index.py")], check=True)

    registry = load_registry(skill_root / "references" / "registry.jsonl")
    by_source_path, by_origin_path = registry_maps(registry)

    entries: List[Dict[str, Any]] = []
    for source_dir in discover_source_dirs(raw_root):
        if selected_sources and source_dir.name not in selected_sources:
            continue
        config = manifest.get(source_dir.name, {})
        entries.append(build_source_entry(skill_root, source_dir.name, config, by_source_path, by_origin_path))

    write_source_index(skill_root / RAW_INDEX_PATH, entries)
    print(
        json.dumps(
            {
                "generated": len(entries),
                "source_index": RAW_INDEX_PATH,
                "status_counts": {
                    status: sum(1 for entry in entries if entry["status"] == status)
                    for status in sorted({entry["status"] for entry in entries})
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
