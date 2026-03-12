#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import sys


def load_ingest_module(skill_root: Path):
    module_path = skill_root / "scripts" / "ingest.py"
    spec = importlib.util.spec_from_file_location("skill_ingest", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def archive_name() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def move_into_archive(skill_root: Path, origin_path: Path, archive_root: Path) -> str:
    try:
        relative = origin_path.relative_to(skill_root / "inbox")
    except ValueError:
        relative = Path(origin_path.name)
    destination = archive_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    counter = 1
    base_destination = destination
    while destination.exists():
        destination = base_destination.with_name(
            f"{base_destination.stem}__{counter}{base_destination.suffix}"
        )
        counter += 1
    shutil.move(str(origin_path), str(destination))
    return str(destination.relative_to(skill_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Process skill inbox files, ingest them, and archive originals.")
    parser.add_argument("--force", action="store_true", help="Rebuild processed outputs even if files were seen before.")
    parser.add_argument("--keep", action="store_true", help="Keep original files in inbox after ingestion.")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild knowledge_index.md after inbox processing.")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    inbox_root = skill_root / "inbox"
    archive_root = inbox_root / "archive" / archive_name()
    inbox_root.mkdir(parents=True, exist_ok=True)

    ingest = load_ingest_module(skill_root)
    discovered = list(ingest.discover_files(inbox_root))
    if not discovered:
        print(json.dumps({"processed": 0, "archived": 0, "message": "Inbox is empty."}, ensure_ascii=False))
        return 0

    records = ingest.ingest_path(skill_root, inbox_root, force=args.force)
    archived = []
    if not args.keep:
        for record in records:
            origin_value = record.get("origin_path")
            if not origin_value:
                continue
            origin_path = (skill_root / origin_value).resolve()
            if not origin_path.exists():
                continue
            try:
                origin_path.relative_to(inbox_root.resolve())
            except ValueError:
                continue
            archived.append(move_into_archive(skill_root, origin_path, archive_root))

    if args.rebuild_index:
        build_index = skill_root / "scripts" / "build_index.py"
        import subprocess

        subprocess.run(["python3", str(build_index)], check=True)

    print(
        json.dumps(
            {
                "processed": len(records),
                "archived": len(archived),
                "archive_root": str(archive_root.relative_to(skill_root)) if archived else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
