# Changelog

This framework is distributed **by copy, not by dependency.** `scripts/bootstrap.py` copies files
into your repo and nothing links the copy back here — no manifest, no version pin, no upgrade
command. So when a defect is fixed in this repo, every tree already carrying it stays broken and
silent. That is the failure this file exists to prevent, which is why each entry leads with
**the files you must re-copy** rather than only with what changed.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with the `Re-copy` line
added for that reason.

## How to pick up a release

Re-copy only the files an entry names. To re-sync a whole stage from a fresh clone:

```bash
git -C /path/to/agent-constitution pull
python /path/to/agent-constitution/scripts/bootstrap.py \
    --dest /path/to/your/repo --stage <your stage> --force
```

`--force` overwrites **every** file in that stage, including the ones you were meant to edit. If
you have filled in your constitution or written real decisions, copy the named files by hand
instead — or `--force` into a scratch directory and diff it against your repo.

**Never re-copy these; they are yours once installed:**

- `CLAUDE.md` and `AGENTS.md` — you filled in the placeholders.
- `docs/DECISIONS.md` and `docs/STATE.md` — your history and your live state.
- `docs/handoffs/INDEX.md` — generated from *your* handoffs by `scripts/librarian.py`.

Scripts, workflows, tests, and the reference documents under `docs/reference/` are safe to replace
wholesale unless you have customized them.

**`scripts/bootstrap.py` is never in your tree.** No stage installs it — you run it *from* the
agent-constitution clone. So a release that changes it needs a `git pull` of the clone, not a
re-copy, and it will never appear in a `Re-copy` line.

## Watching for releases

GitHub → **Watch** → **Custom** → **Releases**. Without that, the paragraph above is a
procedure nobody is ever told to run.

Versions apply to the framework's **contracts**, not to lines of code:

- **MAJOR** — a contract changes such that an unchanged adopter tree starts failing (a gate gets
  stricter, a stamp grammar narrows, a stage manifest drops a file others cite).
- **MINOR** — a new mechanism, stage file, or check; adopting it is optional.
- **PATCH** — a defect fixed with no contract change.

## Cutting a release

1. Promote `[Unreleased]` to the version you are about to tag, and date it.
2. **Check what you are about to tag** — `git checkout main && git pull`, then `git log -1`.
3. Tag that exact commit and push: `git tag -a v0.2.0 -m "v0.2.0" && git push origin v0.2.0`.

Step 1 is not optional bookkeeping. `.github/workflows/release.yml` publishes the section matching
the tag and **fails when there is none**, so a tag pushed against `[Unreleased]` cuts no release at
all.

Step 2 is the one that fails *quietly*, and it is the reason this is a numbered procedure rather
than one command. A tag on a commit that predates the workflow produces **no run, no release, and
no error** — GitHub uses the workflow as it exists at the tagged commit, so there is nothing there
to report the problem. A stale local clone is enough to cause it. The fail-closed design in step 1
cannot help here, because nothing runs to fail. `git log -1` before tagging is the whole guard.

> **Verified the hard way on `v0.2.0`.** The first attempt tagged a stale `main`, silently cut
> nothing, and looked exactly like success at the terminal: `* [new tag] v0.2.0 -> v0.2.0`. The
> tell was the object count — a tag on a commit the remote already has writes **one** object, not
> thirty-seven.

---

## [Unreleased]

_Nothing yet._ Add entries here as changes land, then promote this section to a version
heading before tagging — see **Cutting a release** above.

## [0.2.0] — 2026-08-31

### Re-copy

`scripts/librarian.py`

### Fixed

- **Stage 1 no longer installs a handoff index that fails your first `librarian --check`.**
  `docs/handoffs/INDEX.md` is generated — its own header says so — but it was in the Stage 1
  copy manifest, so every install landed a table whose one row pointed at
  `2026-08-25-public-hardening.md`, a handoff no stage copies. A brand-new repo therefore
  hard-failed its own link check on a tree
  that had done nothing wrong, and carried this project's history into a repo the quickstart
  explicitly tells you not to backfill. `bootstrap.py` now generates the index from the
  destination's own handoffs; `librarian.build_index` takes the directory to render. Regression
  test: `tests/test_bootstrap.py`.
- **The shipped `DECISIONS.md` no longer carries a link that is broken until Stage 4.** It
  referenced `STATE.md` as a sibling, which resolves to `docs/STATE.md` — a file Stage 4
  installs — so every Stage 1–3 tree has reported it broken since the framework was published.

  ⚠️ **Existing adopters: this one is a hand edit, not a re-copy.** Your `docs/DECISIONS.md` is
  your log and must never be overwritten. Open it, find the line under "Never capped" that links
  `STATE.md` as a sibling document, and replace that link with the file name in backticks. New
  installs get the corrected template automatically.

### Added

- **Release notes.** This file, `scripts/changelog_release_notes.py`, and
  `.github/workflows/release.yml`, which publishes the matching section on a `v*` tag and fails the
  release if the tag has no section — so the notes and the tag cannot drift.
- **`tests/test_bootstrap.py`** — installs into a temporary directory and asserts the result
  has no broken links, at Stage 1 and at Stage 4.

### Changed

- **The blank `DECISIONS.md` that Stage 1 installs now lives in `templates/`,** so this project can
  keep its own decision log at `docs/DECISIONS.md`. One path was doing two jobs: the constitution
  requires material decisions to be recorded there, while `bootstrap.py` copied that same file into
  every adopter tree — so any real entry would have shipped this project's history to everyone
  installing the framework, contradicting the "Do not backfill" line `bootstrap.py` prints.
  **The move itself changes nothing for you:** the file still lands at `docs/DECISIONS.md`. The
  link fix below is the part that needs your hand.
- **README quickstart says what a correct install looks like.** Its last step,
  `python scripts/session_brief.py`, prints `docs/STATE.md MISSING` because `STATE.md` arrives at
  Stage 4. `ADOPTION.md` explained that; the README — the front door since the one-command install
  landed — did not, so the documented happy path read as a failed install.

## [0.1.0] — 2026-08-29

The framework as first published: constitution template, append-only decision log, volatile state
ledger with a CI-enforced freshness contract, the craft layer, the review contract, the four
reference scripts, the regression suite, and the Stage 1–4 bootstrap.

⚠️ **Reconstructed from git history.** There was no tag at the time and no changelog was kept,
so this entry is assembled from the commit record rather than written alongside the work. Treat
the file list as authoritative and the summary as INFERRED. Releases from here on are written
with the change · STATUS: CANDIDATE · evidence: `git log 3c1a2d4..94a2860`.

⚠️ **A `v0.1.0` tag cannot be published by CI.** `94a2860` predates both this file and the
release workflow, and a tag push runs the workflow *as it exists at that commit* — that is, not at
all. If you want the tag, create its release by hand from this section; `v0.2.0` is the first
release the workflow can actually cut.

### Re-copy

Everything — this is the baseline.

[Unreleased]: https://github.com/metafive-ai/agent-constitution/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/metafive-ai/agent-constitution/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/metafive-ai/agent-constitution/releases/tag/v0.1.0
