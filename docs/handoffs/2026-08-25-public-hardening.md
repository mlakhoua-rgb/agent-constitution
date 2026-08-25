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

CI on the pull request is the authoritative execution check for this branch. Until it passes, the
implementation remains candidate.

Public-hardening implementation complete on branch `fix/public-hardening-final` · STATUS: CANDIDATE · evidence: `docs/handoffs/2026-08-25-public-hardening.md`
