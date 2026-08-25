#!/usr/bin/env python3
"""Shared parser for STATE.md freshness contracts.

One implementation is used by both session_brief.py and librarian.py so the
human-facing report and the enforcing check cannot silently disagree.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

SECTION_RE = re.compile(r"^## ([A-Z][A-Z /]+?)(?:\s*—\s*(.*))?\s*$")
AS_OF_RE = re.compile(r"as-of:\s*(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class Freshness:
    name: str
    stamp: str | None
    age_days: int | None
    ttl_days: int
    source: str


def _age(stamp: str | None, today: dt.date) -> int | None:
    if not stamp:
        return None
    try:
        return (today - dt.date.fromisoformat(stamp)).days
    except ValueError:
        return None


def section_freshness(
    text: str,
    today: dt.date,
    ttl_days: dict[str, int],
) -> list[Freshness]:
    out: list[Freshness] = []
    for line in text.splitlines():
        match = SECTION_RE.match(line.strip())
        if not match:
            continue
        name = match.group(1).strip()
        ttl = next((v for k, v in ttl_days.items() if name.startswith(k)), None)
        if ttl is None or name.startswith("ACTIVE WORKSTREAMS"):
            continue
        stamp_match = AS_OF_RE.search(match.group(2) or "")
        stamp = stamp_match.group(1) if stamp_match else None
        out.append(Freshness(name, stamp, _age(stamp, today), ttl, "section"))
    return out


def workstream_freshness(
    text: str,
    today: dt.date,
    ttl_days: int,
) -> list[Freshness]:
    """Parse the ACTIVE WORKSTREAMS markdown table and return one record per row."""
    lines = text.splitlines()
    in_section = False
    header_seen = False
    columns: list[str] = []
    out: list[Freshness] = []

    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("## "):
            if stripped.startswith("## ACTIVE WORKSTREAMS"):
                in_section = True
                header_seen = False
                columns = []
                continue
            if in_section:
                break
        if not in_section or not stripped.startswith("|"):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not header_seen:
            normalized = [re.sub(r"[^a-z0-9]+", " ", c.lower()).strip() for c in cells]
            if "workstream" in normalized and "as of" in normalized:
                columns = normalized
                header_seen = True
            continue

        if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        if not cells or len(cells) < len(columns):
            continue

        row = dict(zip(columns, cells))
        name = row.get("workstream", "").strip("` ")
        stamp_raw = row.get("as of", "").strip("` ")
        if not name or name.startswith("<"):
            continue
        stamp = stamp_raw if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp_raw) else None
        out.append(Freshness(name, stamp, _age(stamp, today), ttl_days, "workstream"))

    return out


def all_freshness(
    text: str,
    today: dt.date,
    section_ttls: dict[str, int],
    workstream_ttl: int,
) -> list[Freshness]:
    return section_freshness(text, today, section_ttls) + workstream_freshness(
        text, today, workstream_ttl
    )
