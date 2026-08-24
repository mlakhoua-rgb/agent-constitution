## What this does
<!-- 1–2 sentences -->

## Why
<!-- Link to the Issue -->

## Type of change
- [ ] `chore` / `docs` — no logic change
- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `refactor` — code restructure, no behaviour change

## Verification
- [ ] **Not needed** — chore/docs only
- [ ] **Verified** — describe how below
- [ ] **Not yet verified** ⚠️ — merge blocked until the Owner confirms

### How to verify
<!-- Step-by-step — omit if chore/docs -->

### Edge cases considered
<!-- Especially: what happens when an input is missing, stale, or malformed? -->

---

## Round 0 — author self-review
<!-- Run BEFORE opening and again before EVERY push. -->

- [ ] `python scripts/review_zero.py` — FAILs fixed, WARNs read
- [ ] Full diff self-reviewed as an adversary against `.github/agent-review-guidelines.md`
      (doc claims checked at their cited sources · fail directions named · new keys have consumers)
- [ ] Shared surfaces touched (or "none"):

### The one-sentence risk statement
<!-- "The riskiest claim in this work is ___." This is where re-derivation was mandatory. -->

### Iteration tally
<!-- One row per reviewer round. Tripwire: if findings are not FALLING by round 4, the problem is
     structural — stop iterating and decompose the PR. Budget: ≤10 rounds. -->

| round | findings | fixed in |
|---|---|---|
| 1 | | |

---

## Reviewer checklist
<!-- Fix every finding at its root cause, not its symptom. Every finding needs a commit AND a short
     reply on its own thread (what changed + which commit, or why deferred with a linked Issue) —
     no exceptions, whichever agent is driving. After each fix push, re-request a fresh review of
     the LATEST commit. -->

- [ ] All reviewer findings have a commit + a reply on their thread (or are deferred with a linked Issue)
- [ ] A fresh review **of the latest commit** reports no remaining major issues
- [ ] Iteration budget respected — ≤10 rounds, structural triage at the round-4 tripwire
- [ ] Branch is conflict-free and required CI is green
- [ ] UI change? The Owner reviewed it before merge
