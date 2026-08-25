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
