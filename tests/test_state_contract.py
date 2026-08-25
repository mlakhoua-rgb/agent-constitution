from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from state_contract import all_freshness  # noqa: E402


class StateContractTests(unittest.TestCase):
    def test_workstream_rows_have_independent_ttls(self) -> None:
        text = """\
## NOW — as-of: 2026-08-24

## NEXT — as-of: 2026-08-24

## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `fresh` | agent | active | `2026-08-24` | x |
| `stale` | agent | active | `2026-08-01` | y |
"""
        records = all_freshness(
            text, dt.date(2026, 8, 25), {"NOW": 3, "NEXT": 3}, 7
        )
        rows = {r.name: r for r in records if r.source == "workstream"}
        self.assertEqual(rows["fresh"].age_days, 1)
        self.assertEqual(rows["stale"].age_days, 24)

    def test_missing_workstream_date_is_visible(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `payments` | agent | active | `<YYYY-MM-DD>` | x |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "payments")
        self.assertIsNone(records[0].stamp)
        self.assertIsNone(records[0].age_days)

    def test_future_stamp_is_not_treated_as_fresh(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `payments` | agent | active | `2036-08-25` | x |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].stamp, "2036-08-25")
        self.assertIsNone(records[0].age_days)

    def test_truncated_populated_row_is_not_silently_dropped(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| payments | agent | active | detail |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "payments")
        self.assertIsNone(records[0].stamp)
        self.assertIsNone(records[0].age_days)

    def test_malformed_workstream_header_is_flagged_not_swallowed(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | asof | Detail |
|---|---|---|---|---|
| `payments` | agent | active | `2020-01-01` | x |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        # A misspelled/edited header must not silently disable the row-level
        # guard for every populated row underneath it — it must itself
        # surface as an invalid freshness record.
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0].stamp)
        self.assertIsNone(records[0].age_days)

    def test_populated_row_without_name_is_flagged_not_dropped(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| | agent | active | `2020-01-01` | detail |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        # A real row that lost its name cell but still carries other data
        # must surface as an invalid record, not vanish like the unfilled
        # `<name>` template placeholder row does.
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0].stamp)
        self.assertIsNone(records[0].age_days)

    def test_template_placeholder_row_is_still_silently_skipped(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `<name>` | `<agent / human>` | `<one line>` | `<YYYY-MM-DD>` | `handoffs/<file>.md` |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        self.assertEqual(records, [])

    def test_missing_required_section_is_flagged_not_dropped(self) -> None:
        text = """\
## NEXT — as-of: 2026-08-24

Some content, no NOW heading at all.
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {"NOW": 3, "NEXT": 3}, 7)
        # A required heading that is missing or misspelled must not simply
        # produce no record for it — that reads as "nothing to check"
        # instead of "the freshness contract is disabled here".
        by_name = {r.name: r for r in records}
        self.assertIn("NOW", by_name)
        self.assertIsNone(by_name["NOW"].stamp)
        self.assertIsNone(by_name["NOW"].age_days)
        self.assertEqual(by_name["NEXT"].age_days, 1)

    def test_workstream_section_with_no_table_is_flagged_not_dropped(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

The table itself — header row and all — was removed, but the heading
survived.
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        # The heading being present must not by itself read as "checked" —
        # if no `|` table line survives under it, that's still the whole
        # row-level guard gone, distinct from a header row that's merely
        # missing the required columns.
        workstream_records = [r for r in records if r.source == "workstream"]
        self.assertEqual(len(workstream_records), 1)
        self.assertIsNone(workstream_records[0].stamp)
        self.assertIsNone(workstream_records[0].age_days)

    def test_missing_active_workstreams_section_is_flagged_not_dropped(self) -> None:
        text = """\
## NOW — as-of: 2026-08-24

## NEXT — as-of: 2026-08-24

No ACTIVE WORKSTREAMS heading anywhere in this document.
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {"NOW": 3, "NEXT": 3}, 7)
        # A deleted or misspelled ACTIVE WORKSTREAMS heading must not just
        # produce zero workstream rows — that reads as "no workstreams to
        # check" instead of "the row-level guard is entirely disabled".
        workstream_records = [r for r in records if r.source == "workstream"]
        self.assertEqual(len(workstream_records), 1)
        self.assertIsNone(workstream_records[0].stamp)
        self.assertIsNone(workstream_records[0].age_days)

    def test_suffixed_workstream_heading_does_not_satisfy_presence_check(self) -> None:
        text = """\
## ACTIVE WORKSTREAMSS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `payments` | agent | active | `2020-01-01` | x |
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {}, 7)
        # A typo that preserves the prefix (`ACTIVE WORKSTREAMSS`) must not
        # masquerade as the real heading via a startswith check — the
        # presence guard should still fire, and the table underneath the
        # fake heading stays invisible to it.
        workstream_records = [r for r in records if r.source == "workstream"]
        self.assertEqual(len(workstream_records), 1)
        self.assertEqual(workstream_records[0].name, "ACTIVE WORKSTREAMS section")
        self.assertIsNone(workstream_records[0].stamp)

    def test_suffixed_required_section_heading_does_not_satisfy_presence_check(self) -> None:
        text = """\
## NOWISH — as-of: 2026-08-24

## NEXT — as-of: 2026-08-24
"""
        records = all_freshness(text, dt.date(2026, 8, 25), {"NOW": 3, "NEXT": 3}, 7)
        # A typo that keeps the `NOW` prefix (`NOWISH`) must not satisfy
        # the required-section presence check either.
        by_name = {r.name: r for r in records}
        self.assertIn("NOW", by_name)
        self.assertIsNone(by_name["NOW"].stamp)
        self.assertIsNone(by_name["NOW"].age_days)
        self.assertEqual(by_name["NEXT"].age_days, 1)

    def test_active_workstreams_heading_does_not_need_fake_section_stamp(self) -> None:
        text = """\
## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `payments` | agent | active | `2026-08-25` | x |
"""
        records = all_freshness(
            text, dt.date(2026, 8, 25), {"ACTIVE WORKSTREAMS": 7}, 7
        )
        self.assertEqual([(r.source, r.name) for r in records], [("workstream", "payments")])


if __name__ == "__main__":
    unittest.main()
