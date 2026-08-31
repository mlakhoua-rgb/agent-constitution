# DECISIONS — the durable log

> **The append-only record of decisions: Owner directives and material agent decisions.**
> Newest first. **Never truncated, never rewritten** — a superseded decision gets a new entry that
> names what it supersedes; the old entry stays.

## Why this file exists separately

Decision amnesia is the most expensive of the four agent failure modes, because it is invisible.
A decision gets made, implemented, and forgotten; weeks later a different agent — with equal
confidence and no idea the question was ever settled — reverses it. Nothing in the code says
"this was deliberate." Nothing in the state doc remembers.

Three properties make this file work, and dropping any one of them breaks it:

1. **Append-only.** A rewritten log cannot be trusted as history, and an untrustworthy history
   gets ignored. Reversals are *new entries*, so the reasoning that produced the original
   decision survives alongside the reasoning that overturned it. That pairing is the actual
   asset — future agents need to know a thing was tried and why it failed, not just the current
   answer.
2. **Never capped.** A "last N decisions" section silently drops the (N+1)th on every addition.
   If you find yourself wanting a cap, what you actually want is a separate volatile state file
   — see `docs/STATE.md`, which Stage 4 installs.
3. **Written with the work.** The entry lands in the *same PR* as the change that implements the
   decision. A decision log maintained as a separate chore is a decision log that stops being
   maintained.

## Entry contract

One `- **YYYY-MM-DD** — **headline** …` bullet per decision, dated the day the decision was taken.

- **Quote the Owner's actual words** when the decision is theirs. Paraphrase drifts; a quote is
  evidence. This matters more than it sounds — six weeks later, the difference between "the Owner
  wanted X" and the sentence they actually said is often the whole decision.
- **Link the handoff / Issue / PR** that carries the detail. This file records *what was decided
  and why*; it does not narrate the implementation.
- **Consequential claims carry the stamp grammar** (`docs/reference/evidence-grammar.md`).
- **State what the decision does NOT do.** The most valuable line in most entries.
- **Write against your own interest.** If the decision rests on something unverified, or a seat
  limitation meant you could not check a claim yourself, say so in the entry. An entry that only
  records the flattering half is worse than no entry, because it will be cited as complete.

---

## Example entries

> These are illustrative, showing the shape and the level of honesty expected. Delete them and
> start with your own next real decision — **do not backfill history**, it will be reconstructed
> wrong and then cited as fact.

- **<YYYY-MM-DD>** — **`<COMPONENT>` now fails closed on a missing `<KEY>`, and the fallback
  default is deleted rather than corrected.** Owner, in-session: *"<direct quote of the
  directive>"*. The prior behavior read the key with a silent default, so any payload missing it
  **disarmed the guard** — nothing crashed, nothing logged, the protection simply stopped
  existing. Promoting the key into the required-config set makes the absence a loud halt.
  **What this does NOT do:** it does not backfill existing rows, so a deployment carrying an old
  config will now halt at boot until the key is set — that is intended and is the migration's
  job, not this change's. ⚠️ **Against interest:** this seat could not verify the deployed
  configuration directly and is relying on the Owner's statement that all live rows already carry
  the key; the deploying seat should re-check before rollout.
  **evidence:** `docs/handoffs/<YYYY-MM-DD>-<topic>.md`, PR #<N>.

- **<YYYY-MM-DD>** — **Supersedes the `<X>` decision below: `<the reversal>`.** The original entry
  stays as the record of what was tried and why. What changed is `<the new evidence>` — not a
  change of mind about the goal. **STATUS: VALIDATED · evidence: `<path>`.**

- **<YYYY-MM-DD>** — **The "one command per message" rule is re-scoped to state-mutating commands
  only.** The rule was written from a real incident where a chained command block hid an error
  until downstream work ran on stale data. But the property that failure violated was *acting on
  unread output* — not batching as such. Held at its original width, the rule taxed every
  read-only diagnostic for a year. Naming the actual property let it narrow with the safety
  intact. **Recorded as the worked example of the amendment rule** (`CLAUDE.md §Amending this
  document`): a rule whose *width* is an artifact of the incident that produced it is a
  legitimate challenge target, and challenging it is part of the job.
