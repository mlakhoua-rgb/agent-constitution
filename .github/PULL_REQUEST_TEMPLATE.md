## What this does
<!-- 1–2 sentences -->

## Why
<!-- Link to the Issue -->

## Type of change
- [ ] `chore` / `docs` — no runtime logic change
- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `refactor` — code restructure, no behavior change

## Verification
- [ ] **No runtime verification needed** — docs/chore only; references and material claims still verified
- [ ] **Verified** — describe how below
- [ ] **Not yet verified** ⚠️ — merge blocked until the required verification is complete

### How to verify
<!-- Step-by-step. For docs: cite the source for material/consequential claims and resolve links. -->

### Edge cases considered
<!-- Especially: what happens when an input is missing, stale, malformed, deleted, renamed, or shrunk? -->

---

## Round 0 — author self-review
<!-- Run BEFORE opening and again before EVERY push. -->

- [ ] `python -m unittest discover -s tests -v` — regression tests green
- [ ] `python scripts/review_zero.py` — FAILs fixed, WARNs read
- [ ] Full diff self-reviewed as an adversary against `.github/agent-review-guidelines.md`
      (material doc claims checked at cited sources · fail directions named · new keys have consumers)
- [ ] Shared surfaces touched (or "none"):

### The one-sentence risk statement
<!-- "The riskiest claim in this work is ___." This is where re-derivation is mandatory. -->

### Iteration tally
<!-- One row per reviewer round. Tripwire: if findings are not FALLING by round 4, the problem is
     structural — stop iterating and decompose the PR. Budget: ≤10 rounds. -->

| round | findings | fixed in |
|---|---|---|
| 1 | | |

---

## Reviewer checklist
<!-- Every finding needs a commit AND a short reply on its own thread. An evidence-backed rebuttal
     may resolve a finding for iteration accounting; it does NOT substitute for the independent
     reviewer's latest-commit green light required by the merge gate. -->

- [ ] All reviewer findings have a commit + a reply on their thread (or are deferred with a linked Issue)
- [ ] A fresh review **of the latest commit** reports no remaining major issues
- [ ] Iteration budget respected — ≤10 rounds, structural triage at the round-4 tripwire
- [ ] Branch is conflict-free and required CI is green
- [ ] UI change? The Owner reviewed it before merge
