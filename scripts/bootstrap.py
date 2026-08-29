#!/usr/bin/env python3
"""Copy agent-constitution files into an existing product repo.

Default is Stage 1 (constitution + decision log + scripts + issue templates).
Does not overwrite existing files unless --force is passed.

Usage:
    python scripts/bootstrap.py --dest /path/to/your/repo
    python scripts/bootstrap.py --dest /path/to/your/repo --stage 3 --force
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

STAGES: dict[int, tuple[str, ...]] = {
    1: (
        "CLAUDE.md",
        "AGENTS.md",
        "docs/DECISIONS.md",
        "docs/handoffs/TEMPLATE.md",
        "docs/handoffs/INDEX.md",
        "docs/archive/README.md",
        ".github/ISSUE_TEMPLATE/truth_gap.md",
        ".github/ISSUE_TEMPLATE/backlog_item.md",
        "scripts/session_brief.py",
        "scripts/state_contract.py",
        "scripts/review_zero.py",
        "scripts/librarian.py",
    ),
    2: (
        "docs/reference/agent-operating-manual.md",
        "docs/reference/evidence-grammar.md",
    ),
    3: (
        "docs/reference/review-contract.md",
        ".github/agent-review-guidelines.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/workflows/review-zero.yml",
        "tests/test_review_zero.py",
        "tests/test_state_contract.py",
    ),
    4: (
        "docs/STATE.md",
        ".github/workflows/state-guard.yml",
    ),
}


def files_through(stage: int) -> list[str]:
    out: list[str] = []
    for n in range(1, stage + 1):
        out.extend(STAGES[n])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        required=True,
        type=Path,
        help="Target product repository (must already exist)",
    )
    parser.add_argument(
        "--stage",
        type=int,
        default=1,
        choices=sorted(STAGES),
        help="Highest stage to copy (includes lower stages). Default: 1",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite files that already exist in dest",
    )
    args = parser.parse_args()

    src_root = Path(__file__).resolve().parent.parent
    dest = args.dest.resolve()
    if not dest.is_dir():
        print(f"error: dest is not a directory: {dest}", file=sys.stderr)
        return 2

    copied: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []

    for rel in files_through(args.stage):
        src = src_root / rel
        if not src.exists():
            missing.append(rel)
            continue
        target = dest / rel
        if target.exists() and not args.force:
            skipped.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)

    print(f"stage {args.stage} → {dest}")
    print(f"copied  {len(copied)}")
    print(f"skipped {len(skipped)} (exists; pass --force to replace)")
    if missing:
        print(f"missing {len(missing)} in source clone:")
        for p in missing:
            print(f"  - {p}")

    print()
    print("Next:")
    print("  1. Open CLAUDE.md and fill every <PLACEHOLDER>. Keep it under ~150 lines.")
    print("  2. Start docs/DECISIONS.md with your next real decision. Do not backfill.")
    print("  3. Create the labels the templates expect:")
    print('       gh label create truth-gap --color B60205 --description "Two sources of truth disagree"')
    if args.stage >= 4:
        print('       gh label create state:no-change --color ededed --description "This PR changes no project state"')
    print("  4. python scripts/session_brief.py")
    print("  5. Read ADOPTION.md before turning on Stage 3/4 CI gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
