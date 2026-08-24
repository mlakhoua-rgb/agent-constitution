#!/usr/bin/env python3
"""Librarian — the daily knowledge-base maintenance pass.

Docs rot silently. Nobody notices, because the rot is invisible until an agent
cites a stale line with total confidence. This script makes the rot LOUD and,
where possible, fixes it mechanically.

What it does:
  1. Regenerates the PLATFORM STATE auto-block in docs/STATE.md from ground
     truth (git tip, migration head, open-issue count). Anything derivable is
     derived — hand-editing that block is the exact failure this file prevents.
  2. Stamps / clears STALE banners on STATE.md sections whose `as-of` date
     exceeds its TTL class.
  3. Regenerates docs/handoffs/INDEX.md so every handoff is reachable.
  4. Checks every markdown link under docs/ plus the root-level *.md entry
     points (README, CLAUDE.md, ADOPTION, …). Broken links in STATE.md and
     INDEX.md are HARD failures; elsewhere they are warnings.
  5. Reports ORPHANS — docs not reachable from STATE.md by following links.
     An unreachable doc is a doc that gets rewritten from scratch by the next
     agent who needs it. Root-level files are entry points, not orphan
     candidates; docs/archive/ is exempt because unreachable is the point.
  6. Enforces the STATE.md size budget (bytes AND per-line length).

     Budget BYTES, not lines. A line cap is trivially satisfiable by
     concatenating whole updates onto single enormous lines — which is what
     actually happens — leaving a file that cannot be read in one pass by the
     agents required to read it first.

Usage:
    python scripts/librarian.py --check    # validate only; exit 1 on hard failures
    python scripts/librarian.py --write    # apply regenerations, then validate

Run from anywhere in the repo. Standard library only; uses `git`/`gh` when
available and degrades gracefully when not.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

# --- CONFIGURATION — edit for your repo ------------------------------------

TTL_DAYS = {"NOW": 3, "NEXT": 3, "ACTIVE WORKSTREAMS": 7}
STATE_MAX_BYTES = 48 * 1024
STATE_MAX_LINE_CHARS = 1200
MIGRATIONS_DIR_MARKER = "alembic/versions"
DEFAULT_BRANCH_CANDIDATES = ("origin/main", "origin/master", "origin/maintenance")

#: Docs excluded from the orphan report (entry points and generated files).
ORPHAN_EXEMPT = {"docs/STATE.md", "docs/DECISIONS.md", "docs/handoffs/INDEX.md",
                 "docs/handoffs/TEMPLATE.md"}

# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
STATE_MD = REPO / "docs/STATE.md"
DOCS = REPO / "docs"
HANDOFFS = DOCS / "handoffs"
INDEX_MD = HANDOFFS / "INDEX.md"

AUTO_START = "<!-- librarian:auto-start -->"
AUTO_END = "<!-- librarian:auto-end -->"
# Match the heading FIRST, then look for the date inside its remainder. Folding
# the date into the heading pattern makes a malformed stamp fail to match at all
# — the section then vanishes from the report instead of being flagged unstamped.
SECTION_RE = re.compile(r"^## ([A-Z][A-Z /]+?)(?:\s*—\s*(.*))?\s*$")
AS_OF_RE = re.compile(r"as-of:\s*(\d{4}-\d{2}-\d{2})")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# Consumes the banner line AND any blank lines following it. Without the trailing
# `(?:[ \t]*\n)*`, every --write re-strips the banner but leaves its blank line
# behind, then adds a fresh one — so a daily cron injects two blank lines per
# section per day and silently eats the byte budget. Verified idempotent.
STALE_BANNER_RE = re.compile(r"^> ⚠️ \*\*STALE\*\*.*(?:\n|$)(?:[ \t]*\n)*", re.MULTILINE)
HANDOFF_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")


def git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(REPO), *args],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def gh_open_issues() -> str:
    if not shutil.which("gh"):
        return "unknown (gh unavailable)"
    try:
        out = subprocess.run(["gh", "issue", "list", "--state", "open",
                              "--limit", "1000", "--json", "number"],
                             capture_output=True, text=True, check=True,
                             timeout=20, cwd=str(REPO)).stdout
        return str(out.count('"number"'))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown (gh call failed)"


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


# --- 1. auto-block ----------------------------------------------------------

def build_auto_block() -> str:
    ref = next((r for r in DEFAULT_BRANCH_CANDIDATES
                if git("rev-parse", "--verify", "--quiet", r) is not None), None)
    tip = git("log", "-1", "--format=%h %ad %s", "--date=short", ref) if ref else None
    migrations = sorted(p for p in REPO.glob(f"**/{MIGRATIONS_DIR_MARKER}/*.py")
                        if p.name != "__init__.py")
    lines = [
        f"*Generated {today().isoformat()} by `scripts/librarian.py`. Do not hand-edit.*",
        "",
        f"- **Default branch tip:** {tip or 'unknown (no origin ref)'}",
        f"- **Migration head:** {migrations[-1].name if migrations else 'n/a'}"
        f" ({len(migrations)} total)",
        f"- **Open issues:** {gh_open_issues()}",
    ]
    return "\n".join(lines)


def replace_auto_block(text: str, block: str) -> tuple[str, bool]:
    if AUTO_START not in text or AUTO_END not in text:
        return text, False
    pre, rest = text.split(AUTO_START, 1)
    _, post = rest.split(AUTO_END, 1)
    return f"{pre}{AUTO_START}\n{block}\n{AUTO_END}{post}", True


# --- 2. STALE banners -------------------------------------------------------

def stale_sections(text: str) -> list[tuple[str, str | None, int, int]]:
    """[(section, as_of, age_days, ttl)] for TTL-classed sections."""
    out = []
    for line in text.splitlines():
        m = SECTION_RE.match(line.strip())
        if not m:
            continue
        name = m.group(1).strip()
        d = AS_OF_RE.search(m.group(2) or "")
        stamp = d.group(1) if d else None
        ttl = next((v for k, v in TTL_DAYS.items() if name.startswith(k)), None)
        if ttl is None:
            continue
        age = (today() - dt.date.fromisoformat(stamp)).days if stamp else 10**6
        out.append((name, stamp, age, ttl))
    return out


def apply_stale_banners(text: str) -> str:
    text = STALE_BANNER_RE.sub("", text)
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        out.append(line)
        m = SECTION_RE.match(line.strip())
        if not m:
            continue
        name = m.group(1).strip()
        d = AS_OF_RE.search(m.group(2) or "")
        stamp = d.group(1) if d else None
        ttl = next((v for k, v in TTL_DAYS.items() if name.startswith(k)), None)
        if ttl is None:
            continue
        if stamp is None:
            out.append("")
            out.append(f"> ⚠️ **STALE** — section carries no `as-of:` stamp (TTL {ttl}d).")
            continue
        age = (today() - dt.date.fromisoformat(stamp)).days
        if age > ttl:
            out.append("")
            out.append(
                f"> ⚠️ **STALE** — as-of {stamp} is {age}d old (TTL {ttl}d). "
                f"Re-verify the substance, then re-stamp."
            )
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


# --- 3. handoff index -------------------------------------------------------

def build_index() -> str:
    rows = []
    if HANDOFFS.exists():
        for p in sorted(HANDOFFS.glob("*.md"), reverse=True):
            if p.name in {"INDEX.md", "TEMPLATE.md"}:
                continue
            m = HANDOFF_NAME_RE.match(p.name)
            date, topic = (m.group(1), m.group(2).replace("-", " ")) if m else ("", p.stem)
            rows.append(f"| {date} | [{topic}]({p.name}) |")
    body = "\n".join(rows) if rows else "| | *none yet* |"
    return (
        "# Handoff index\n\n"
        f"*Generated {today().isoformat()} by `scripts/librarian.py`. Do not hand-edit.*\n\n"
        "| date | topic |\n|---|---|\n" + body + "\n"
    )


# --- 4/5. links and orphans -------------------------------------------------

def md_files() -> list[Path]:
    files = [p for p in DOCS.rglob("*.md")] if DOCS.exists() else []
    # Root-level entry points (README, CLAUDE.md, ADOPTION, …) rot exactly like
    # docs/ does, and they are the files a first-time reader hits first.
    files += sorted(REPO.glob("*.md"))
    return files


def check_links() -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    for p in md_files():
        rel = p.relative_to(REPO).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for target in MD_LINK_RE.findall(text):
            if re.match(r"^(https?:|mailto:|#|<)", target):
                continue
            clean = target.split("#", 1)[0].strip()
            if not clean:
                continue
            resolved = (p.parent / clean).resolve()
            if resolved.exists():
                continue
            msg = f"{rel}: broken link → {target}"
            if rel in {"docs/STATE.md", "docs/handoffs/INDEX.md"}:
                hard.append(msg)
            else:
                soft.append(msg)
    return hard, soft


def find_orphans() -> list[str]:
    if not STATE_MD.exists():
        return []
    reachable: set[Path] = set()
    frontier = [STATE_MD.resolve()]
    while frontier:
        cur = frontier.pop()
        if cur in reachable or not cur.exists() or cur.suffix != ".md":
            continue
        reachable.add(cur)
        try:
            text = cur.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for target in MD_LINK_RE.findall(text):
            if re.match(r"^(https?:|mailto:|#|<)", target):
                continue
            clean = target.split("#", 1)[0].strip()
            if clean:
                frontier.append((cur.parent / clean).resolve())

    orphans = []
    for p in md_files():
        rel = p.relative_to(REPO).as_posix()
        # Root-level files are entry points, not orphan candidates; archive/ is
        # exempt because unreachable is the point.
        if "/" not in rel or rel in ORPHAN_EXEMPT or "archive/" in rel:
            continue
        if p.resolve() not in reachable:
            orphans.append(rel)
    return sorted(orphans)


# --- 6. budget --------------------------------------------------------------

def check_budget() -> list[str]:
    if not STATE_MD.exists():
        return [f"{STATE_MD.relative_to(REPO)} is missing"]
    text = STATE_MD.read_text(encoding="utf-8")
    problems = []
    size = len(text.encode("utf-8"))
    if size > STATE_MAX_BYTES:
        problems.append(
            f"STATE.md is {size/1024:.1f} KB, over the {STATE_MAX_BYTES/1024:.0f} KB budget "
            f"— it POINTS, it does not narrate; move detail into a handoff"
        )
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > STATE_MAX_LINE_CHARS:
            problems.append(
                f"STATE.md:{i} is {len(line)} chars, over the {STATE_MAX_LINE_CHARS} cap"
            )
    return problems


# --- driver -----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate only")
    mode.add_argument("--write", action="store_true", help="regenerate, then validate")
    args = ap.parse_args()

    hard_failures: list[str] = []

    if args.write:
        if STATE_MD.exists():
            text = STATE_MD.read_text(encoding="utf-8")
            text, replaced = replace_auto_block(text, build_auto_block())
            if not replaced:
                print(f"  ! no {AUTO_START} / {AUTO_END} markers in STATE.md — auto-block skipped")
            text = apply_stale_banners(text)
            STATE_MD.write_text(text, encoding="utf-8")
            print("  ✓ STATE.md auto-block + STALE banners regenerated")
        if HANDOFFS.exists():
            INDEX_MD.write_text(build_index(), encoding="utf-8")
            print(f"  ✓ {INDEX_MD.relative_to(REPO)} regenerated")

    print("\nLIBRARIAN CHECK\n" + "─" * 40)

    if STATE_MD.exists():
        for name, stamp, age, ttl in stale_sections(STATE_MD.read_text(encoding="utf-8")):
            if stamp is None:
                hard_failures.append(f"STATE.md §{name} has no as-of stamp")
                print(f"  ✗ §{name}: no as-of stamp")
            elif age > ttl:
                hard_failures.append(f"STATE.md §{name} is stale ({age}d > {ttl}d)")
                print(f"  ✗ §{name}: STALE — as-of {stamp}, {age}d old (TTL {ttl}d)")
            else:
                print(f"  ✓ §{name}: fresh — as-of {stamp} ({age}d)")

    hard_links, soft_links = check_links()
    for m in hard_links:
        hard_failures.append(m)
        print(f"  ✗ {m}")
    for m in soft_links:
        print(f"  ! {m}")
    if not hard_links and not soft_links:
        print("  ✓ all markdown links resolve")

    for m in check_budget():
        hard_failures.append(m)
        print(f"  ✗ {m}")

    orphans = find_orphans()
    for o in orphans:
        print(f"  ! orphan (unreachable from STATE.md): {o}")
    if not orphans:
        print("  ✓ no orphaned docs")

    print("─" * 40)
    if hard_failures:
        print(f"{len(hard_failures)} hard failure(s). Fix, or run --write to regenerate.")
        return 1
    print("clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
