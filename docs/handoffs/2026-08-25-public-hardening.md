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
