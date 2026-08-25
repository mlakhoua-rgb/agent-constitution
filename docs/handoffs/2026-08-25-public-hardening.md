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

## Round 4 — Codex re-review on commit `32d410e` found two more issues

- **P1 — the round-3 citation-shift check only ran on files that net-shrank.** `citation_line_shifted`
  was gated on `cited in change.shrunk`, so a file that lost a line before an existing citation but
  also gained a line elsewhere (net same size, or even growing) never entered `shrunk` and the check
  never ran, even though the cited line number now names different content. `impact()` now derives a
  separate `restructured` set from any file with at least one diff hunk whose old/new line counts
  differ — independent of net file size — and the shift check runs whenever a cited file is in either
  set; the EOF-exceeded check stays scoped to `shrunk` specifically, since only a net-shrinking file
  can newly break that bound. See `review_zero.py`,
  `test_restructured_non_shrinking_file_shifts_existing_citation`.
- **P1 — deleting the ACTIVE WORKSTREAMS heading itself disables the whole row-level guard.** Both
  consumers' required-section maps (`SECTION_TTLS`) only ever listed `NOW`/`NEXT`; `workstream_freshness`
  had no presence check of its own, so a deleted or misspelled `## ACTIVE WORKSTREAMS` heading simply
  produced zero workstream rows — indistinguishable from "no workstreams exist yet". The function now
  tracks whether the heading was seen at all and, if not, emits an invalid record — distinct from the
  existing "malformed table header" case, which fires only when the heading is present but its column
  row isn't. See `state_contract.py`, `test_missing_active_workstreams_section_is_flagged_not_dropped`.

Both are fixed and regression-tested; `python -m unittest discover -s tests -v` (17/17) and
`python scripts/review_zero.py --base origin/main` are clean (only the pre-existing size WARN).

Codex round-4 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, `tests/test_review_zero.py`, this handoff.

## Round 5 — Codex re-review on commit `9ad5919` found two more issues

- **P1 — a workstream table removed out from under a surviving heading was invisible.** The round-4
  presence check only asked whether `## ACTIVE WORKSTREAMS` was seen at all; if the heading survived
  but every `|` table line beneath it — header row included — was deleted, `header_checked` stayed
  `False` with no record emitted for it, same blind spot one level down. Now: heading absent → invalid
  "section" record (round 4, unchanged); heading present but no table line ever seen → a new invalid
  "table" record; heading and a header row present but the columns are wrong → existing "malformed
  header" record (round 2, unchanged). See `state_contract.py`,
  `test_workstream_section_with_no_table_is_flagged_not_dropped`.
- **P1 — the round-3/4 shift check false-positived on a deletion strictly after the citation.** Git's
  zero-context hunk for a pure deletion anchors `new_start` on the new-file line *preceding* the cut
  (deleting old line 4 produces `@@ -4 +3,0 @@`), so the inclusive `new_start <= num` check treated
  "deleted right after line 3" the same as "deleted at or before line 3" and failed an unaffected
  citation. `citation_line_shifted` now computes a boundary that's exclusive for zero-length deletion
  hunks (`new_start + 1`) and inclusive for hunks that add real content (`new_start`), matching where
  the cut or insertion actually sits. See `review_zero.py`,
  `test_deletion_strictly_after_cited_line_does_not_false_positive`.

Both are fixed and regression-tested; `python -m unittest discover -s tests -v` (19/19) and
`python scripts/review_zero.py --base origin/main` are clean (only the pre-existing size WARN).

Codex round-5 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, `tests/test_review_zero.py`, this handoff.

## Round 6 — Codex re-review on commit `86ea925` found two more issues

- **P1 — a citation the PR itself fixes in the same commit was re-flagged as broken.**
  `check_impacted_references` re-validated every citation in the current HEAD document against the
  base-relative shift/deletion checks, with no way to tell "unchanged since base" apart from "just
  written or corrected by this PR" — so updating a citation from `src/foo.py:3` to `src/foo.py:2` in
  the same commit that deletes an earlier line still failed as shifted, blocking the exact repair the
  required CI gate was asking for. The function now takes the PR's added-line set and skips any line
  the PR itself wrote or edited — those are already validated against current HEAD directly by
  `check_added_citations`/`check_added_md_links`. See `review_zero.py`,
  `test_citation_fixed_in_same_pr_is_not_reflagged_as_shifted`.
- **P1 — a suffixed heading still satisfied the presence checks added in rounds 4 and 5.** Both the
  `## ACTIVE WORKSTREAMS` and the required-section (`NOW`/`NEXT`) presence checks used `startswith`
  against the heading text, so a typo that preserves the prefix (`## ACTIVE WORKSTREAMSS`, `## NOWISH`)
  still satisfied them and let a fresh table pass with the real heading gone. Both now compare the
  exact heading name parsed by `SECTION_RE` against the required name/key, not a prefix — proactively
  hardened `section_freshness`'s general `NOW`/`NEXT` matching the same way, since it shared the
  identical prefix-typo weakness Codex had only flagged on the workstream heading. See
  `state_contract.py`, `test_suffixed_workstream_heading_does_not_satisfy_presence_check`,
  `test_suffixed_required_section_heading_does_not_satisfy_presence_check`.

Both are fixed and regression-tested; `python -m unittest discover -s tests -v` (22/22) and
`python scripts/review_zero.py --base origin/main` are clean (only the pre-existing size WARN).

Codex round-6 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, `tests/test_review_zero.py`, this handoff.

## Round 7 — Codex re-review on commit `afd344b` found three more issues

- **P1 — the round-6 line-skip fix could hide a citation the PR actually broke.** Skipping an entire
  edited line (round 6) exempted every reference on it, not just the one the edit touched — a line
  edited for an unrelated reason that still carried an untouched, now-broken citation verbatim would
  be skipped by the impact scan, and `check_added_citations` also misses it whenever the deleted
  target's containing directory was removed too (its own directory-exists heuristic goes empty-handed).
  `check_impacted_references` no longer skips by line; it now compares each individual link
  target/citation against a base-content set (resolved link targets, `(path, num)` citation pairs)
  built from that same document at `base`, and only exempts a reference that doesn't appear there
  verbatim — an untouched reference still matches exactly and gets checked; an edited/new one won't
  match and is already covered by `check_added_md_links`/`check_added_citations`. This removes the
  `added` parameter entirely — reference-level comparison needs no line-membership tracking. See
  `review_zero.py`, `test_unrelated_edit_on_same_line_does_not_hide_a_broken_citation`.
- **P1 — `not-as-of:` parsed as a valid `as-of:` stamp.** `AS_OF_RE` searched for `as-of:` anywhere in
  the heading metadata with no boundary, so a malformed marker like `## NOW — not-as-of: 2026-08-24`
  matched on the substring and was read as fresh. Added a negative lookbehind so a preceding word
  character or hyphen (as in `not-as-of:`) blocks the match. See `state_contract.py`,
  `test_not_as_of_marker_is_not_parsed_as_a_valid_stamp`.
- **P1 — a duplicated required table column silently picked one value.** The header-presence check
  only asked whether `workstream`/`as-of` were *present* in the normalized column list, so a header
  like `| Workstream | as-of | as-of |` passed; `dict(zip(columns, cells))` then kept only the last
  `as-of` cell, hiding a stale value in the first nominal date column behind a fresh second one. The
  check now requires exactly one of each required column, not merely "at least one" — a duplicate
  fails the header the same way a missing column already did. See `state_contract.py`,
  `test_duplicate_required_workstream_column_is_flagged_not_swallowed`.

All three are fixed and regression-tested; `python -m unittest discover -s tests -v` (25/25) and
`python scripts/review_zero.py --base origin/main` are clean (only the pre-existing size WARN).

Codex round-7 fixes are validated by local regression tests and `review_zero.py` · STATUS: VALIDATED · evidence: `tests/test_state_contract.py`, `tests/test_review_zero.py`, this handoff.
