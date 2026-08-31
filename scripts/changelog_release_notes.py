#!/usr/bin/env python3
"""Print one release's notes from CHANGELOG.md.

`.github/workflows/release.yml` publishes exactly what this prints, and this exits
non-zero when the requested version has no section. That coupling is the point: a
tag pushed without a changelog entry fails the release instead of publishing an
empty body, so the notes and the tag cannot drift apart unnoticed.

Usage:
    python scripts/changelog_release_notes.py --version v0.2.0
    python scripts/changelog_release_notes.py --version Unreleased
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
RELEASE_HEADING_RE = re.compile(r"^##\s+")
# Trailing `[0.2.0]: https://…` definitions belong to the document, not to the last
# release. Without stripping them the final section silently absorbs every link
# definition in the file — and the last section is the one a fresh tag publishes.
LINK_DEFINITION_RE = re.compile(r"^\[[^\]]+\]:\s")
# A `##` heading is a release only if it opens with a version-shaped token. The
# changelog's own prose sections are `##` too, and a looser rule would let
# `## How to pick up a release` answer to a request for "How".
VERSION_TOKEN_RE = re.compile(r"^(?:v?\d+(?:\.\d+)*(?:[-+][\w.]+)?|unreleased)$", re.IGNORECASE)


def normalize(version: str) -> str:
    return version.strip().removeprefix("v").casefold()


def heading_version(line: str) -> str | None:
    """Return the version named by a `## …` heading, or None if it names none."""
    rest = RELEASE_HEADING_RE.sub("", line).strip()
    match = re.match(r"^\[([^\]]+)\]|^(\S+)", rest)
    if not match:
        return None
    token = match.group(1) or match.group(2)
    return token if VERSION_TOKEN_RE.match(token) else None


def extract(text: str, version: str) -> str:
    wanted = normalize(version)
    body: list[str] | None = None
    for line in text.splitlines():
        if RELEASE_HEADING_RE.match(line):
            if body is not None:
                break
            found = heading_version(line)
            if found is not None and normalize(found) == wanted:
                body = []
            continue
        if body is not None:
            body.append(line)

    if body is None:
        return ""
    while body and (not body[-1].strip() or LINK_DEFINITION_RE.match(body[-1])):
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    return "\n".join(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True,
                        help="Release to print, with or without the leading `v`")
    parser.add_argument("--changelog", type=Path, default=DEFAULT_CHANGELOG,
                        help=f"Changelog to read. Default: {DEFAULT_CHANGELOG.name}")
    args = parser.parse_args()

    if not args.changelog.is_file():
        print(f"error: no changelog at {args.changelog}", file=sys.stderr)
        return 2

    notes = extract(args.changelog.read_text(encoding="utf-8"), args.version)
    if not notes:
        print(
            f"error: {args.changelog.name} has no notes for {args.version}. "
            "Add its section before tagging — a release published with an empty body "
            "tells adopters nothing about which files to re-copy.",
            file=sys.stderr,
        )
        return 1

    print(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
