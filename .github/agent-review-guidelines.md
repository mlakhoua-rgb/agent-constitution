# Agent PR-review guidelines

These instructions steer **both** the automated reviewer and the author's own Round-0 self-review.
The reviewer reads this file **and** the repo's `CLAUDE.md` (root + the `services/<svc>/CLAUDE.md`
of any touched service) before commenting.

**Tune the review by editing this file — no CI change needed.** A rubric that requires a workflow
change to adjust is a rubric that stops being adjusted.

This is an **agentic, repo-aware** reviewer: it can open any file, trace call paths, and run
read-only `git`/`gh` to understand context beyond the diff. Use that — most real defects are
cross-file, and deletions/renames can invalidate trusted references without adding a single line.

## What this repo is

<2–4 sentences: stack, what it does, and — critically — **what the consequences of a defect
actually are.** Reviewers calibrate severity off this paragraph. Overstating it inflates every
judgment call; understating it does the reverse. Get it accurate and keep it accurate.>

---

## Standing invariants — check every PR against these

> Replace with your own. **The selection criterion is: each invariant has caused, or nearly caused,
> a real incident.** Five invariants you can defend beat twenty copied from articles.

1. **FAIL DIRECTION.** For any gate, guard, or check: what happens when its input is missing,
   stale, or malformed? Protective logic must fail **CLOSED**, never silently open. Flag any
   latch/flag that, once set, is never re-validated.
2. **STALENESS.** Any externally-fed value used in a decision must have an age check.
   **"Available" is not "fresh."**
3. **UNITS & RANGES.** Thresholds must state units and be asserted at config-load/boot, so a
   wrong-unit value fails loudly rather than silently disabling the rule.
4. **BOUNDARIES & ROUNDING.** Check behavior at minimums, step rounding, and clipping.
   Risk-*reducing* adjustments must never round *up*; prefer reject over clamp.
5. **ENUM / STRING DRIFT.** Comparisons against string literals of enum values are silent no-ops
   waiting to happen — require normalization at the boundary plus a canary test pinning the set.
6. **MIGRATIONS.** Exactly one head before and after; every migration has an explicit working
   `downgrade()`; backfills are additive only and never mutate operational switches.
7. **ORPHAN CONFIG.** Any new key must have a code consumer; any new consumer must have its key in
   defaults + validation + the required-keys set. No hardcoded defaults for a consequential
   parameter — a missing one must HALT, never silently fall back.
8. **TEST vs. LIVE DIVERGENCE.** Any wall-clock, feed-age, or alerting logic must state its
   behavior in each mode explicitly. Flag look-ahead or future-data leaks.
9. **ALERTS.** Notifications fire on state transitions only, never per-cycle. Anything meaning a
   protection is not active right now is an INCIDENT, not a footnote.
10. **<YOUR FROZEN SURFACE>.** Name the values that change only via an evidence-backed process —
    then flag any incidental drive-by change to them even when the diff looks harmless.

---

## <Recurring footgun> — the type/serialization trap

> Every codebase has one or two. Document yours here with the exact guard required. Example shape:
>
> A JSONB column can hold an object, array, JSON `null`, SQL `NULL`, or a scalar. `->`, `->>`,
> `jsonb_object_keys()`, `?`, `@>` all error on scalars and JSON `null`. Require a
> `WHERE jsonb_typeof(col) = 'object'` guard before any object/array operator.

---

## How to comment

- **Inline on the specific changed line** for concrete issues; top-level for cross-cutting ones.
- **Severity-tag everything:** `[P0]` broken/unsafe · `[P1]` likely bug/risk · `[P2]` should fix ·
  `[P3]` nit/optional.
- **Priority order:** correctness on the consequential path > fail-direction > data integrity >
  migration safety > tests > everything else.
- **Do not comment on style.** No formatting, naming-taste, or micro-perf nits.
- **Be specific and actionable:** name the failure mode and the input that triggers it. No praise,
  no summary of what the PR does, no generic advice.
- **Review the code that is there, not the code you would have written.** An unfamiliar structure
  or an approach you would not have chosen is not a finding unless you can name the input that
  makes it fail or the invariant it breaks.
- **Scope findings to the diff and its blast radius.** Pre-existing defects the PR merely sits near
  belong in an Issue. A deleted/renamed/shrunk target is in blast radius for all inbound references
  because this PR can invalidate them.
- **An evidence-backed rebuttal resolves the finding for iteration accounting.** Do not re-raise it
  without new evidence. It does **not** count as the required independent green light on the latest
  commit.

---

## Mandatory verdict comment — every review, even clean

Finish **every** review with exactly one top-level verdict comment, **including when the diff is
clean.** Without it, a clean PR is indistinguishable from one nothing reviewed. Never manufacture
findings to fill it.

The **first line must be exactly** one of:

- `**<Reviewer> review — CLEAN**`
- `**<Reviewer> review — N finding(s)**`

Then one line naming what you actually traced. If not clean, list each finding as
`[P0]–[P3] <one-line> → <link to its inline comment>`.

This stamp is the required audit trail — it is NOT the forbidden praise/summary, and it does not
replace the inline comments, which still carry the actual findings.

---

## Docs / markdown PRs

Apply the same rigor to **material claims**: flag a consequential persisted claim lacking the stamp
grammar (`STATUS: CANDIDATE|VALIDATED|REJECTED · evidence: <path>`), a mislabeled result, a dead
cross-reference, a citation invalidated by a deleted/renamed/shrunk target, or a contradiction with
`CLAUDE.md`. **A wrong doc is worse than a missing one, because it is trusted.**
