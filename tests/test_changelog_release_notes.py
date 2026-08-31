from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap import STAGES, files_through  # noqa: E402
from changelog_release_notes import extract  # noqa: E402

# `\Z` matters: the last release's Re-copy section has no heading after it, and
# without it this check silently skipped the one section nearest the tag.
RE_COPY_SECTION_RE = re.compile(r"^### Re-copy\n(.*?)(?=^#{2,3} |\Z)",
                                re.MULTILINE | re.DOTALL)
REPO_PATH_RE = re.compile(r"`([\w.-]+(?:/[\w.-]+)+\.\w+)`")

CHANGELOG = """\
# Changelog

Preamble prose.

## How to pick up a release

Not a release section.

## [Unreleased]

### Added

- something pending

## [0.2.0] - 2026-09-01

### Re-copy

`scripts/bootstrap.py`

## [0.1.0] - 2026-08-29

Baseline.

[Unreleased]: https://example.invalid/compare/v0.2.0...HEAD
[0.2.0]: https://example.invalid/releases/tag/v0.2.0
[0.1.0]: https://example.invalid/releases/tag/v0.1.0
"""


class ExtractTests(unittest.TestCase):
    def test_released_version_stops_at_the_next_heading(self) -> None:
        self.assertEqual(
            extract(CHANGELOG, "v0.2.0"), "### Re-copy\n\n`scripts/bootstrap.py`"
        )

    def test_leading_v_is_optional(self) -> None:
        self.assertEqual(extract(CHANGELOG, "0.2.0"), extract(CHANGELOG, "v0.2.0"))

    def test_unreleased_section_is_addressable(self) -> None:
        self.assertEqual(extract(CHANGELOG, "Unreleased"), "### Added\n\n- something pending")

    def test_missing_version_yields_no_notes(self) -> None:
        # The release workflow turns this into a failed release rather than a
        # release published with an empty body.
        self.assertEqual(extract(CHANGELOG, "v9.9.9"), "")

    def test_last_section_does_not_absorb_trailing_link_definitions(self) -> None:
        # The link definitions sit under the final release heading, so a naive
        # "read to EOF" sweeps the whole document's URLs into that release body.
        self.assertEqual(extract(CHANGELOG, "v0.1.0"), "Baseline.")

    def test_non_version_headings_are_not_matched(self) -> None:
        self.assertEqual(extract(CHANGELOG, "How"), "")

    def test_every_version_the_release_workflow_advertises_has_notes(self) -> None:
        # Codex round 1, P1: release.yml documented `git tag -a v0.2.0` while
        # CHANGELOG.md held only [Unreleased] and [0.1.0]. Following the documented
        # command exited 1 and cut no release — the one path a maintainer copies
        # verbatim was the one path guaranteed to fail.
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        advertised = sorted(set(re.findall(r"git tag -a (v\d[\w.+-]*)", workflow)))
        self.assertTrue(advertised, "release.yml should document a concrete tag command")
        for version in advertised:
            self.assertNotEqual(
                extract(changelog, version).strip(), "",
                f"release.yml advertises {version}, which has no CHANGELOG.md section",
            )

    def test_every_released_section_in_the_shipped_changelog_has_notes(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        versions = re.findall(r"^## \[(\d[^\]]*)\]", changelog, re.MULTILINE)
        self.assertTrue(versions, "the shipped changelog should carry released versions")
        for version in versions:
            self.assertNotEqual(extract(changelog, version).strip(), "", version)

    def test_re_copy_lines_only_name_files_an_adopter_actually_holds(self) -> None:
        # A Re-copy line naming a file no stage installs sends the reader looking for
        # something that is not in their tree — and the whole point of these entries
        # is that they are actionable. `scripts/bootstrap.py` is run from the clone,
        # never installed, and was wrongly listed in 0.2.0's first draft.
        installed = set(files_through(max(STAGES)))
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for section in RE_COPY_SECTION_RE.findall(changelog):
            for path in REPO_PATH_RE.findall(section):
                self.assertIn(
                    path, installed,
                    f"a Re-copy line names {path}, which no stage installs",
                )

    def test_shipped_changelog_last_section_excludes_link_definitions(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertNotIn("releases/tag", extract(changelog, "0.1.0"))


if __name__ == "__main__":
    unittest.main()
