from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from changelog_release_notes import extract  # noqa: E402

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

    def test_shipped_changelog_has_notes_for_unreleased(self) -> None:
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertNotEqual(extract(text, "Unreleased").strip(), "")
        self.assertNotIn("releases/tag", extract(text, "0.1.0"))


if __name__ == "__main__":
    unittest.main()
