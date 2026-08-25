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
        parsed = dt.date.fromisoformat(stamp)
    except ValueError:
        return None
    if parsed > today:
        # A future stamp is never valid evidence of freshness — a typo'd
        # year (e.g. 2036 instead of 2026) must not read as "0 days old".
        return None
    return (today - parsed).days


def section_freshness(
    text: str,
    today: dt.date,
    ttl_days: dict[str, int],
) -> list[Freshness]:
    out: list[Freshness] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = SECTION_RE.match(line.strip())
        if not match:
            continue
        name = match.group(1).strip()
        key = next((k for k in ttl_days if name.startswith(k)), None)
        if key is None:
            continue
        if name.startswith("ACTIVE WORKSTREAMS"):
            # ACTIVE WORKSTREAMS carries no section-level stamp of its own —
            # freshness comes from workstream_freshness's per-row records —
            # but the heading being present still counts as "not missing".
            seen.add(key)
            continue
        seen.add(key)
        stamp_match = AS_OF_RE.search(match.group(2) or "")
        stamp = stamp_match.group(1) if stamp_match else None
        out.append(Freshness(name, stamp, _age(stamp, today), ttl_days[key], "section"))

    for key, ttl in ttl_days.items():
        if key not in seen:
            # A required heading (e.g. `## NOW`) that is absent or misspelled
            # must not silently disappear from the record set — it disables
            # that part of the freshness contract with no failure to show
            # for it. Synthesize an invalid record so it fails closed.
            out.append(Freshness(key, None, None, ttl, "section"))
    return out


def workstream_freshness(
    text: str,
    today: dt.date,
    ttl_days: int,
) -> list[Freshness]:
    """Parse the ACTIVE WORKSTREAMS markdown table and return one record per row."""
    lines = text.splitlines()
    in_section = False
    section_seen = False
    header_checked = False
    header_seen = False
    columns: list[str] = []
    out: list[Freshness] = []

    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("## "):
            if stripped.startswith("## ACTIVE WORKSTREAMS"):
                in_section = True
                section_seen = True
                header_checked = False
                header_seen = False
                columns = []
                continue
            if in_section:
                break
        if not in_section or not stripped.startswith("|"):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not header_checked:
            # Only the first table row in the section is a header candidate.
            # If it doesn't declare the columns we need, the table is
            # malformed — report that as an invalid freshness record instead
            # of silently re-trying every later row as a fresh "header"
            # (which would swallow the whole table without ever failing).
            header_checked = True
            normalized = [re.sub(r"[^a-z0-9]+", " ", c.lower()).strip() for c in cells]
            if "workstream" in normalized and "as of" in normalized:
                columns = normalized
                header_seen = True
            else:
                out.append(Freshness(
                    "ACTIVE WORKSTREAMS table header", None, None, ttl_days, "workstream"
                ))
            continue
        if not header_seen:
            continue

        if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        if not cells:
            continue
        if len(cells) < len(columns):
            # A populated row with fewer cells than the header (a dropped
            # trailing column) must still be validated, not vanish from the
            # record set — pad the missing trailing cells as empty so a
            # missing `as-of` value surfaces as a freshness failure instead
            # of silently disappearing.
            cells = cells + [""] * (len(columns) - len(cells))

        row = dict(zip(columns, cells))
        name = row.get("workstream", "").strip("` ")
        stamp_raw = row.get("as of", "").strip("` ")
        if name.startswith("<"):
            # Unfilled template placeholder row (`<name>`) — not a real
            # workstream, nothing to validate.
            continue
        if not name:
            # A populated row that lost its name cell is still a real row
            # with real data — reserve the silent skip for the template
            # placeholder above, and report this one instead of letting a
            # malformed or stale workstream disappear from the record set.
            if any(c.strip("` ") for c in cells):
                out.append(Freshness(
                    "<unnamed workstream row>", None, None, ttl_days, "workstream"
                ))
            continue
        stamp = stamp_raw if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp_raw) else None
        out.append(Freshness(name, stamp, _age(stamp, today), ttl_days, "workstream"))

    if not section_seen:
        # A deleted or misspelled `## ACTIVE WORKSTREAMS` heading must not
        # just yield an empty row set — that reads as "no workstreams to
        # check" instead of "the entire row-level freshness guard is gone".
        out.append(Freshness("ACTIVE WORKSTREAMS section", None, None, ttl_days, "workstream"))
    elif not header_checked:
        # The heading survived but every `|` table line under it — header
        # included — was removed, so no header candidate was ever seen.
        # Distinct from the malformed-header case (a header row present but
        # missing the required columns), which already reports itself.
        out.append(Freshness("ACTIVE WORKSTREAMS table", None, None, ttl_days, "workstream"))

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
