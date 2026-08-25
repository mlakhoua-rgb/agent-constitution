# Handoff — public hardening

**Date:** 2026-08-25

## Scope

Close the public-review findings against the reference implementation and its contracts:

- deletion/rename/shrink referential-integrity blind spot in `review_zero.py`;
- ACTIVE WORKSTREAMS TTL mismatch between prose and implementation;
- missing regression tests for executable governance claims;
- over-broad VERIFIED / INFERRED / ASSUMED labeling language;
- vendor-neutral content vs. `CLAUDE.md` filename ambiguity;
- docs/chore verification contradiction in the PR template;
- `session_brief.py` claiming CI truth without checking current-branch CI;
- rebuttal-resolution vs. independent-approval ambiguity;
- missing public security-reporting policy.

## Material implementation decisions

- Local semantic mechanical checks remain scoped to added lines, but referential-integrity checks
  inspect existing inbound references when a target is deleted, renamed, or shrunk. This preserves
  blast-radius isolation without allowing deletion-only false-cleans.
- STATE freshness parsing is centralized in `scripts/state_contract.py`; NOW/NEXT use heading dates,
  while ACTIVE WORKSTREAMS rows are checked independently from their own `as-of` cells.
- Regression tests use only `unittest` and temporary git repositories to preserve the project's
  Python 3.10+ / standard-library-only contract.
- `CLAUDE.md` remains canonical for auto-discovery compatibility; the docs now state explicitly
  that filename discovery and governance authority are separate concerns.

## Verification

On PR #2, both required workflows passed on commit `2427097874139aaf03da963037cca2bca4d6985c`:

- Review Zero run `32843448222`: regression tests **success** and mechanical Round-0 **success**.
- STATE Guard run `32843448167`: `STATE.md touched or state:no-change` **success**.

This evidence validates the executable claims covered by those tests and gates. The independent
Codex review was separately requested with `@codex review`; merge remains blocked until that review
has evaluated the latest commit, per the review contract.

Public-hardening implementation is validated by CI on PR #2 · STATUS: VALIDATED · evidence: PR #2 / workflow runs `32843448222`, `32843448167`.

## Round 1 — Codex review findings closed

The requested `@codex review` on commit `2427097874139aaf03da963037cca2bca4d6985c` returned three
findings, all fixed in this PR with a regression test each:

- **P1 — future freshness stamps read as fresh.** `state_contract._age` computed
  `(today - stamp).days` unconditionally, so a stamp with a future year (e.g. a `2036` typo) produced
  a negative age that both `session_brief.py` and `librarian.py --check` treat as "not stale" since
  it is never greater than the TTL. `_age` now returns `None` for any stamp later than `today`, which
  both consumers already render as "no valid as-of date". See `state_contract.py`,
  `test_future_stamp_is_not_treated_as_fresh`.
- **P1 — truncated populated workstream rows vanish.** A populated row with fewer cells than the
  header (a dropped trailing column, e.g. a missing `as-of` cell) was matched by
  `len(cells) < len(columns)` and skipped outright, so `librarian.py --check` never saw — and never
  failed — that row. Truncated rows are now right-padded with empty cells before parsing, so a
  missing `as-of` value surfaces as a normal freshness failure instead of disappearing from the
  record set. See `state_contract.py`, `test_truncated_populated_row_is_not_silently_dropped`.
- **P2 — directory links survive their last file's deletion.** `Impact.deleted` only ever held file
  paths from `git diff --name-status`, so a markdown link whose target is a directory (e.g. a
  `guide/` path) that lost its last tracked file in a deletion-only diff resolved clean: the
  directory path was never in `deleted`. `impact()` now also derives `deleted_dirs` as the set
  difference between the base and HEAD directory trees, and `check_impacted_references` treats a
  link resolving into either set as broken. See `review_zero.py`,
  `test_deleting_last_file_in_directory_breaks_existing_directory_link`.

All three regressions are encoded under `tests/` and pass locally
(`python -m unittest discover -s tests -v`); `scripts/review_zero.py --base origin/main` reports
`0 FAIL` on the round-1 commit (one pre-existing size WARN, unrelated to this scope).

Codex round-1 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, `tests/test_review_zero.py`, this handoff.

## Round 2 — Codex re-review on commit `1c397d4` found two more issues

- **P1 — the round-1 handoff bullet's own illustrative directory-link example broke Review Zero.**
  Writing the directory-link example as literal bracket/parenthesis markdown-link syntax made
  `review_zero.py`'s own added-line link check parse it as a real link to a nonexistent path,
  failing the required CI job. Reworded to describe the target in prose (commit `faccb40`); the
  same commit also joined a wrapped `STATUS`/`evidence:` line that was tripping the status-grammar
  WARN for the identical single-line-scan reason (commit `4d32f5e`).
- **P1 — a malformed ACTIVE WORKSTREAMS header disables the whole row-level guard.** Every
  unrecognized `|`-prefixed line in the section was retried as a header candidate forever, so a
  misspelled or edited header column (e.g. `as-of` becoming `asof`) never set `header_seen` — no
  row underneath it, however stale, was ever parsed as data, and `librarian.py --check` reported no
  failures at all for that table. Only the first table row in the section is now treated as a
  header candidate; if it doesn't declare the required columns, that is itself reported as an
  invalid freshness record instead of the whole table silently vanishing. See `state_contract.py`,
  `test_malformed_workstream_header_is_flagged_not_swallowed`.

Both are fixed and regression-tested; `python -m unittest discover -s tests -v` and
`python scripts/review_zero.py --base origin/main` are clean (only the pre-existing size WARN).

Codex round-2 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, this handoff.

## Round 3 — Codex re-review on commit `e803167` found three more issues

- **P1 — a populated workstream row without a name cell is dropped, not flagged.** The nameless-row
  skip used the same branch as the unfilled `<name>` template placeholder, so a real row that lost
  its first cell (still carrying owner/status/date/detail data) vanished from the record set exactly
  like an intentionally-empty template row does. The template placeholder (`name.startswith("<")`)
  is still skipped silently; any other populated-but-nameless row now emits an invalid freshness
  record instead. See `state_contract.py`, `test_populated_row_without_name_is_flagged_not_dropped`.
- **P1 — a missing or misspelled required section heading produces no record at all.**
  `section_freshness` only ever emitted a record when it found a matching heading, so a deleted or
  misspelled `## NOW` disappeared from the output with fresh NOW/NEXT surrounding it hiding nothing
  — there was no failure to see. The function now tracks which required keys were actually matched
  and synthesizes an invalid record for any that never appeared (the `ACTIVE WORKSTREAMS` heading
  still counts as present without needing its own stamp, since its freshness comes from
  `workstream_freshness`). See `state_contract.py`, `test_missing_required_section_is_flagged_not_dropped`.
- **P1 — a citation surviving EOF can still point at shifted content.** The shrink check only
  compared the cited line number against the new end-of-file, so a deletion earlier in the file that
  shifts every later line up by one (e.g. line 3 used to be "three", now names what was line 4) read
  as clean whenever the number stayed within bounds. `check_impacted_references` now also inspects
  the file's diff hunks: any hunk with an unequal old/new line count at or before the cited line
  number marks the citation as impacted, not just an out-of-bounds one. See `review_zero.py`,
  `test_shrunk_source_with_earlier_deletion_shifts_existing_citation`.

All three are fixed and regression-tested; `python -m unittest discover -s tests -v` (15/15) and
`python scripts/review_zero.py --base origin/main` are clean (only the pre-existing size WARN).

Codex round-3 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, `tests/test_review_zero.py`, this handoff.
