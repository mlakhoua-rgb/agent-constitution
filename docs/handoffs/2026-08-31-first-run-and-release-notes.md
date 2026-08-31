# Handoff — first-run audit and release notes

**Date:** 2026-08-31

## Scope

Two questions, taken in order:

1. Does the documented Stage 1 install actually work in a repo that has never seen this framework?
2. This repo has no release channel. Adopters hold copies of these files and nothing tells them
   when one is fixed. Build the mechanism that closes that.

## Method

`scripts/bootstrap.py` was run into empty temporary directories at Stage 1 and Stage 4, and every
copied script was then executed from inside the destination, exactly as the README's quickstart
tells an adopter to. Findings were then checked against `ADOPTION.md` and the CI workflows before
being called defects — which is what killed most of them.

## Audit — four candidates, one defect

Three candidates were **REJECTED** on inspection. They are recorded because a later session will
otherwise re-raise them:

- *"`docs/STATE.md` is missing after a Stage 1 install."* Deliberate and documented:
  `ADOPTION.md:58` explains that the scripts ship at Stage 1 while `STATE.md` arrives at Stage 4.
- *"`librarian.py --check` exits non-zero on a fresh tree."* Documented at `ADOPTION.md:151`,
  "Expected on a fresh clone."
- *"CI never runs the regression suite."* Wrong. `.github/workflows/review-zero.yml:33` runs
  `python -m unittest discover -s tests -v`. The original grep looked for `pytest` and a bare
  `tests/` argument and missed `-s tests`.

Three of four candidate findings were rejected against the documented contract ·
STATUS: REJECTED · evidence: `ADOPTION.md`, `.github/workflows/review-zero.yml`.

One survived.

**`docs/handoffs/INDEX.md` was in the Stage 1 copy manifest, and it is a generated file.** Its own
header says "Do not hand-edit." Every Stage 1 install therefore landed a table with one row
pointing at `2026-08-25-public-hardening.md` — a handoff no stage copies. Two consequences, both
silent from inside this repo:

- the adopter's very first `librarian.py --check` hard-failed on a broken link in a tree that had
  done nothing wrong (`scripts/librarian.py` classifies `INDEX.md` link breakage as hard);
- it backfilled this project's history into a repo whose own quickstart tells the adopter not to
  backfill history.

Reproduced before the fix and confirmed absent after · STATUS: VALIDATED · evidence:
`tests/test_bootstrap.py`.

## Material implementation decisions

- **The index is generated for the destination, never copied.** `librarian.build_index` now takes
  the handoffs directory to render, and `bootstrap.py` calls it against the destination after the
  copy pass, honoring the same exists/`--force` semantics as a copied file. Deleting it from the
  manifest alone was not enough: `docs/STATE.md` links the index, and `librarian` treats a broken
  `STATE.md` link as a hard failure, so a Stage 4 adopter would have traded one hard failure for
  another unless `bootstrap.py` produced the file itself.
- **Release notes are keyed to re-copy sets, not to changes.** This framework is distributed by
  copy with no manifest, pin, or upgrade command, so "what changed" is not actionable for an
  adopter; "which files you now hold a stale version of" is. Every `CHANGELOG.md` entry leads with
  a `Re-copy` line, and the preamble names the files that must *never* be re-copied because they
  became the adopter's at install.
- **The release body is extracted from the changelog, and a tag without a section fails the
  release.** `.github/workflows/release.yml` publishes what `scripts/changelog_release_notes.py`
  prints for the pushed tag. A release notification whose body is empty reads as "nothing you need
  to do" — strictly worse than no notification — so the two cannot be allowed to drift.
- **Versioning starts at `0.1.0` for what is already public, and says it was reconstructed.**
  There was no tag and no changelog when that work shipped, so the entry is assembled from the
  commit record. It is labelled in the file itself rather than presented as if it were written
  with the work.

## Verification

- `python -m unittest discover -s tests -v` — 50 tests, all passing (39 pre-existing, 11 added).
- The four `tests/test_bootstrap.py` cases were run against the pre-fix `scripts/bootstrap.py`
  from `origin/main`: two fail there, naming `2026-08-25-public-hardening.md` as the broken link.
  A regression test that passes against the bug it describes is not a regression test.
- `python scripts/review_zero.py --base origin/main` — clean.
- `scripts/changelog_release_notes.py` was exercised against a released version, `Unreleased`, and
  a version with no section; the last exits 1, which is what fails the release job.

⚠️ **Against interest:** the release workflow itself has not been executed. No tag exists in
this repository, and pushing one publishes a public GitHub Release — an outward-facing action
this seat did not take on its own authority. Its Python half is covered by
`tests/test_changelog_release_notes.py`; its YAML half is unproven until the first tag.

Release workflow YAML is unexecuted; its first run is the real test ·
STATUS: CANDIDATE · evidence: `.github/workflows/release.yml`.

## Not done

- **No tag was pushed.** Cutting `v0.1.0` at `94a2860` and `v0.2.0` at this change's merge commit
  is the Owner's call; the changelog sections for both are in place.
- **No CI gate requires a changelog entry.** The requirement is stated in `CONTRIBUTING.md`
  instead. A gate here is defensible and was deliberately not added in the same change as the
  mechanism it would guard.
