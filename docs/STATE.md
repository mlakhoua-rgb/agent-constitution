# STATE — <PROJECT NAME>

> **The workstream ledger and hand-written intent layer.** This file answers *where we are* and
> *where we're going*; everything else is one link away.
>
> The session-start read is **`python scripts/session_brief.py`**, not this file — the script
> derives repository/GitHub/CI context live and prints freshness verdicts on this file's sections
> and workstream rows. Agents then open this file for NOW/NEXT intent and the workstream ledger.

## The three contracts that keep this file honest

Without all three, a state doc becomes a 30,000-token narrative that everyone cites and nobody
reads.

**1. Write-with-the-work.** Any PR that changes project state updates its workstream row — and
NOW/NEXT if they changed — *in the same PR*. CI-enforced: a PR must touch this file or carry the
`state:no-change` label (`.github/workflows/state-guard.yml`). A state doc updated as a separate
chore is a state doc that stops being updated.

**2. This file POINTS, it does not narrate.** Detail lives in `docs/handoffs/<date>-<topic>.md`.
Budget-enforced by `scripts/librarian.py`: **≤ 48 KB total and ≤ 1,200 characters per line.**

> **Why a byte budget and not a line cap.** A line cap is trivially satisfiable by concatenating
> whole updates onto single enormous lines. Budget bytes *and* line length, or the constraint is
> decorative.

**3. Freshness contract.** NOW and NEXT carry heading-level `as-of: YYYY-MM-DD` stamps with a
3-day TTL. **Every populated ACTIVE WORKSTREAMS row carries its own `as-of` value with a 7-day
TTL.** `scripts/session_brief.py` reports each row independently and `scripts/librarian.py --check`
hard-fails stale or missing row dates, so one newly refreshed workstream cannot mask another stale
one.

A daily Librarian pass also validates links, orphans, and the size budget. Drift it flags is closed
by an agent `--write` PR.

> **Staleness legend.** `as-of` = the date the section or row's **substance** was last verified,
> not the date the text was edited. Live infrastructure state is only trustworthy from a seat with
> access to it — re-verify before acting.

*last-librarian-pass: <YYYY-MM-DD>*

---

## PLATFORM STATE — auto-generated, do not hand-edit

<!-- librarian:auto-start -->
*Not yet generated — run `python scripts/librarian.py --write`.*
<!-- librarian:auto-end -->

> Everything between those markers is regenerated from ground truth (git tip, migration head, open
> issue count). **Hand-editing it is the exact failure this file exists to prevent.** If a fact can
> be derived, derive it; hand-write only decisions and intent.

---

## NOW — as-of: <YYYY-MM-DD>

**🎯 <One-line headline of what is actually happening right now.>**

<2–5 sentences maximum. What changed, what it means, what is blocked. Link the handoff for
detail — do not narrate it here.>

> ⚠️ **SUPERSEDED <YYYY-MM-DD>** — when a NOW item is overtaken, mark it superseded rather than
> deleting it, and put the new item above. A NOW section that silently rewrites itself loses the
> "what did we think last week" thread that makes it useful in a post-mortem.

## NEXT — as-of: <YYYY-MM-DD>

Ordered. The order encodes a belief about what matters most — which means it is *checkable*. An
agent whose session evidence contradicts the ordering should say so, with the evidence, in the
same breath as the work it did.

1. **<Item>** — <one line: the deliverable, not the activity> · `<Issue #>`
2. **<Item>** — <…>

## ACTIVE WORKSTREAMS

| Workstream | Owner seat | Status | as-of | Detail |
|---|---|---|---|---|
| `<name>` | `<agent / human>` | `<one line>` | `<YYYY-MM-DD>` | `handoffs/<file>.md` |

> The `as-of` cell is required for every real row and is validated independently. Do not add a
> section-level date here; that would make a fresh heading capable of hiding stale rows.

## MAP

Every document under `docs/` should be reachable from here by following links — the Librarian
reports orphans. An unreachable doc is a doc that will be rewritten from scratch by the next agent
who needs it.

- [Decisions](DECISIONS.md) — the append-only durable log
- [Agent operating manual](reference/agent-operating-manual.md) — how to work
- [Review contract](reference/review-contract.md) — gates and merge rules
- [Evidence grammar](reference/evidence-grammar.md) — claim stamps and labels
- [Handoff index](handoffs/INDEX.md) — generated
