#!/usr/bin/env python3
"""Librarian — knowledge-base freshness and integrity maintenance.

Regenerates derived state, validates freshness contracts, links, orphan reachability,
and STATE.md size. NOW/NEXT freshness is section-level; ACTIVE WORKSTREAMS is
validated row-by-row so one fresh row can never mask another stale row.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

from state_contract import all_freshness

SECTION_TTLS = {"NOW": 3, "NEXT": 3}
WORKSTREAM_TTL = 7
STATE_MAX_BYTES = 48 * 1024
STATE_MAX_LINE_CHARS = 1200
MIGRATIONS_DIR_MARKER = "alembic/versions"
DEFAULT_BRANCH_CANDIDATES = ("origin/main", "origin/master", "origin/maintenance")
ORPHAN_EXEMPT = {
    "docs/STATE.md", "docs/DECISIONS.md", "docs/handoffs/INDEX.md",
    "docs/handoffs/TEMPLATE.md",
}

REPO = Path(__file__).resolve().parent.parent
STATE_MD = REPO / "docs/STATE.md"
DOCS = REPO / "docs"
HANDOFFS = DOCS / "handoffs"
INDEX_MD = HANDOFFS / "INDEX.md"
AUTO_START = "<!-- librarian:auto-start -->"
AUTO_END = "<!-- librarian:auto-end -->"
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HANDOFF_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")


def git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def gh_open_issues() -> str:
    if not shutil.which("gh"):
        return "unknown (gh unavailable)"
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--limit", "1000", "--json", "number"],
            capture_output=True, text=True, check=True, timeout=20, cwd=str(REPO),
        ).stdout
        return str(out.count('"number"'))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown (gh call failed)"


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def build_auto_block() -> str:
    ref = next(
        (r for r in DEFAULT_BRANCH_CANDIDATES
         if git("rev-parse", "--verify", "--quiet", r) is not None), None
    )
    tip = git("log", "-1", "--format=%h %ad %s", "--date=short", ref) if ref else None
    migrations = sorted(
        p for p in REPO.glob(f"**/{MIGRATIONS_DIR_MARKER}/*.py") if p.name != "__init__.py"
    )
    return "\n".join([
        f"*Generated {today().isoformat()} by `scripts/librarian.py`. Do not hand-edit.*",
        "",
        f"- **Default branch tip:** {tip or 'unknown (no origin ref)'}",
        f"- **Migration head:** {migrations[-1].name if migrations else 'n/a'} ({len(migrations)} total)",
        f"- **Open issues:** {gh_open_issues()}",
    ])


def replace_auto_block(text: str, block: str) -> tuple[str, bool]:
    if AUTO_START not in text or AUTO_END not in text:
        return text, False
    pre, rest = text.split(AUTO_START, 1)
    _, post = rest.split(AUTO_END, 1)
    return f"{pre}{AUTO_START}\n{block}\n{AUTO_END}{post}", True


def build_index() -> str:
    rows: list[str] = []
    if HANDOFFS.exists():
        for path in sorted(HANDOFFS.glob("*.md"), reverse=True):
            if path.name in {"INDEX.md", "TEMPLATE.md"}:
                continue
            match = HANDOFF_NAME_RE.match(path.name)
            date, topic = (
                (match.group(1), match.group(2).replace("-", " "))
                if match else ("", path.stem)
            )
            rows.append(f"| {date} | [{topic}]({path.name}) |")
    body = "\n".join(rows) if rows else "| | *none yet* |"
    return (
        "# Handoff index\n\n"
        f"*Generated {today().isoformat()} by `scripts/librarian.py`. Do not hand-edit.*\n\n"
        "| date | topic |\n|---|---|\n" + body + "\n"
    )


def md_files() -> list[Path]:
    files = list(DOCS.rglob("*.md")) if DOCS.exists() else []
    files += sorted(REPO.glob("*.md"))
    return files


def check_links() -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    for path in md_files():
        rel = path.relative_to(REPO).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for target in MD_LINK_RE.findall(text):
            if re.match(r"^(https?:|mailto:|#|<)", target):
                continue
            clean = target.split("#", 1)[0].strip()
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            if resolved.exists():
                continue
            message = f"{rel}: broken link → {target}"
            if rel in {"docs/STATE.md", "docs/handoffs/INDEX.md"}:
                hard.append(message)
            else:
                soft.append(message)
    return hard, soft


def find_orphans() -> list[str]:
    if not STATE_MD.exists():
        return []
    reachable: set[Path] = set()
    frontier = [STATE_MD.resolve()]
    while frontier:
        current = frontier.pop()
        if current in reachable or not current.exists() or current.suffix != ".md":
            continue
        reachable.add(current)
        try:
            text = current.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for target in MD_LINK_RE.findall(text):
            if re.match(r"^(https?:|mailto:|#|<)", target):
                continue
            clean = target.split("#", 1)[0].strip()
            if clean:
                frontier.append((current.parent / clean).resolve())

    orphans: list[str] = []
    for path in md_files():
        rel = path.relative_to(REPO).as_posix()
        if "/" not in rel or rel in ORPHAN_EXEMPT or "archive/" in rel:
            continue
        if path.resolve() not in reachable:
            orphans.append(rel)
    return sorted(orphans)


def check_budget() -> list[str]:
    if not STATE_MD.exists():
        return ["docs/STATE.md is missing"]
    text = STATE_MD.read_text(encoding="utf-8")
    problems: list[str] = []
    size = len(text.encode("utf-8"))
    if size > STATE_MAX_BYTES:
        problems.append(
            f"STATE.md is {size / 1024:.1f} KB, over {STATE_MAX_BYTES / 1024:.0f} KB"
        )
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > STATE_MAX_LINE_CHARS:
            problems.append(
                f"STATE.md:{lineno} is {len(line)} chars, over {STATE_MAX_LINE_CHARS}"
            )
    return problems


def check_freshness(text: str) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    reports: list[str] = []
    records = all_freshness(text, today(), SECTION_TTLS, WORKSTREAM_TTL)
    for record in records:
        prefix = f"§{record.name}" if record.source == "section" else f"workstream `{record.name}`"
        if record.stamp is None or record.age_days is None:
            failures.append(f"{prefix} has no valid as-of date")
            reports.append(f"  ✗ {prefix}: no valid as-of date (TTL {record.ttl_days}d)")
        elif record.age_days > record.ttl_days:
            failures.append(f"{prefix} is stale ({record.age_days}d > {record.ttl_days}d)")
            reports.append(
                f"  ✗ {prefix}: STALE — as-of {record.stamp}, {record.age_days}d old "
                f"(TTL {record.ttl_days}d)"
            )
        else:
            reports.append(
                f"  ✓ {prefix}: fresh — as-of {record.stamp} ({record.age_days}d, TTL {record.ttl_days}d)"
            )
    return failures, reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate only")
    mode.add_argument("--write", action="store_true", help="regenerate derived blocks, then validate")
    args = parser.parse_args()

    hard_failures: list[str] = []
    if args.write:
        if STATE_MD.exists():
            text = STATE_MD.read_text(encoding="utf-8")
            text, replaced = replace_auto_block(text, build_auto_block())
            if not replaced:
                print(f"  ! no {AUTO_START} / {AUTO_END} markers in STATE.md — auto-block skipped")
            STATE_MD.write_text(text, encoding="utf-8")
            print("  ✓ STATE.md auto-block regenerated")
        if HANDOFFS.exists():
            INDEX_MD.write_text(build_index(), encoding="utf-8")
            print(f"  ✓ {INDEX_MD.relative_to(REPO)} regenerated")

    print("\nLIBRARIAN CHECK\n" + "─" * 40)
    if STATE_MD.exists():
        failures, reports = check_freshness(STATE_MD.read_text(encoding="utf-8"))
        hard_failures.extend(failures)
        for report in reports:
            print(report)
    else:
        hard_failures.append("docs/STATE.md is missing")
        print("  ✗ docs/STATE.md is missing")

    hard_links, soft_links = check_links()
    for message in hard_links:
        hard_failures.append(message)
        print(f"  ✗ {message}")
    for message in soft_links:
        print(f"  ! {message}")
    if not hard_links and not soft_links:
        print("  ✓ all markdown links resolve")

    for message in check_budget():
        hard_failures.append(message)
        print(f"  ✗ {message}")

    orphans = find_orphans()
    for orphan in orphans:
        print(f"  ! orphan (unreachable from STATE.md): {orphan}")
    if not orphans:
        print("  ✓ no orphaned docs")

    print("─" * 40)
    if hard_failures:
        print(f"{len(hard_failures)} hard failure(s).")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
