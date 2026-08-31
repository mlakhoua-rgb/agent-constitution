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

## Watching for releases

GitHub → **Watch** → **Custom** → **Releases**. Without that, the paragraph above is a
procedure nobody is ever told to run.

Versions apply to the framework's **contracts**, not to lines of code:

- **MAJOR** — a contract changes such that an unchanged adopter tree starts failing (a gate gets
  stricter, a stamp grammar narrows, a stage manifest drops a file others cite).
- **MINOR** — a new mechanism, stage file, or check; adopting it is optional.
- **PATCH** — a defect fixed with no contract change.

---

## [Unreleased]

### Re-copy

`scripts/bootstrap.py` · `scripts/librarian.py`

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

### Added

- **Release notes.** This file, `scripts/changelog_release_notes.py`, and
  `.github/workflows/release.yml`, which publishes the matching section on a `v*` tag and fails the
  release if the tag has no section — so the notes and the tag cannot drift.
- **`tests/test_bootstrap.py`** — installs into a temporary directory and asserts the result
  has no broken links, at Stage 1 and at Stage 4.

### Changed

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

### Re-copy

Everything — this is the baseline.

[Unreleased]: https://github.com/metafive-ai/agent-constitution/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/metafive-ai/agent-constitution/releases/tag/v0.1.0
