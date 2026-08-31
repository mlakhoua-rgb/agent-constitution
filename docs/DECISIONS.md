# DECISIONS — the durable log

> **This project's own append-only record**: Owner directives and material agent decisions about
> the framework itself. Newest first. **Never truncated, never rewritten** — a superseded decision
> gets a new entry naming what it supersedes; the old entry stays.

**Entry contract:** [`templates/DECISIONS.md`](../templates/DECISIONS.md) — the same contract this
project ships to adopters, and the blank `scripts/bootstrap.py` installs. This file is the working
instance of it.

**Started 2026-08-31, not backfilled.** Decisions taken before that date live in
[`handoffs/`](handoffs/INDEX.md) and are deliberately not transcribed here: reconstructing them
from commit messages and memory is the failure `ADOPTION.md` warns about, and a log that mixes
recorded decisions with reconstructed ones is worse than one that starts honestly.

---

- **2026-08-31** — **`docs/DECISIONS.md` is now this project's real log; the blank it ships moves
  to `templates/DECISIONS.md`.** One path was doing two incompatible jobs: `CLAUDE.md §Delivery`
  requires material decisions to be recorded here, while `scripts/bootstrap.py` copied this exact
  file into every adopter tree — so writing a real entry would have shipped this project's history
  to everyone who installs the framework, contradicting the "Do not backfill" line
  `bootstrap.py` itself prints. `templates/` now holds what an adopter gets; everything else in the
  tree is ours. **What this does NOT do:** it does not change where the file lands in an adopter's
  repo (still `docs/DECISIONS.md`), so no adopter needs to re-copy anything; and it does not give
  `CLAUDE.md` the same treatment, which is a larger change to the document every agent reads first
  and is deliberately left alone. Closes the truth-gap in Issue #4, raised by Codex round-2 review
  of PR #3 · STATUS: VALIDATED · evidence: `tests/test_bootstrap.py`, Issue #4.

- **2026-08-31** — **This project deliberately keeps no `docs/STATE.md` of its own; the shipped
  file stays a template, and PRs here carry `state:no-change`.** A real state ledger commits this
  repo to a **3-day TTL on NOW and NEXT** (`scripts/librarian.py:21`). A repo that receives
  occasional PRs will miss that within a fortnight, and `ADOPTION.md §Stage 4` says exactly what
  happens next: a gate that cannot be satisfied gets disabled. Choosing not to adopt Stage 4 here
  is the honest reading of our own advice, not an oversight. **What this does NOT do:** it does not
  remove `STATE.md` from Stage 4 or weaken the freshness contract for adopters — for a system with
  live workstreams the TTL is the point. ⚠️ **Against interest:** this means the framework does
  not dogfood its own state ledger, and a reader may weigh that when judging the contract.
  Recorded so the absence reads as a decision rather than a gap somebody later "fixes."

- **2026-08-31** — **`docs/handoffs/INDEX.md` is generated for the destination, never copied.**
  It is a derived file whose own header says "Do not hand-edit"; shipping ours gave every fresh
  install a table pointing at a handoff no stage copies, so a brand-new repo hard-failed its own
  `librarian --check`. `scripts/bootstrap.py` now renders it from the destination's handoffs.
  **What this does NOT do:** it does not stop `librarian.py --write` from regenerating the file
  normally, and it does not exempt `INDEX.md` from the hard link check — a broken row there should
  still fail. Recorded because the next agent reading the Stage 1 manifest will see a file the
  constitution references and no copy step, and reversing it is a one-line change.
  ⚠️ Transcribed from `handoffs/2026-08-31-first-run-and-release-notes.md`, written the same day
  by the session that took the decision — not reconstructed.
  PR #3 · STATUS: VALIDATED · evidence: `tests/test_bootstrap.py`.
