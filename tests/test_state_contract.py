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
