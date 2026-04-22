#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified entrypoint for retained raw-source checking and processing."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply configured processing rules to raw sources. Default is check-only.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild outputs even if they already exist.",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Optional raw source directory name under references/raw/sources. Repeat to limit scope.",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild knowledge_index.md after apply.",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    sync_script = skill_root / "scripts" / "sync_raw_sources.py"

    command = ["python3", str(sync_script)]
    if args.apply:
        command.append("--apply")
    if args.force:
        command.append("--force")
    if args.rebuild_index:
        command.append("--rebuild-index")
    for source in args.source or []:
        command.extend(["--source", source])

    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
