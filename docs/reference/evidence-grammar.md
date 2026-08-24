# Evidence Grammar — how claims carry their provenance

Two mechanisms. The **labels** apply to every sentence an agent writes. The **stamp** applies to
consequential claims that outlive the session.

---

## 1. The three labels — VERIFIED / INFERRED / ASSUMED

Every claim in a deliverable goes in one bin, **labeled where the reader will see it.**

| Label | Means | Test |
|---|---|---|
| **VERIFIED** | You looked. | Can you name the file, line, query, or command output? If not, it isn't verified. |
| **INFERRED** | Follows from verified facts by reasoning you state. | Is the reasoning written down, or only in your head? |
| **ASSUMED** | You need it true and have not checked. | **Ships with its blast radius attached.** |

**An assumption is not a failure — an unlabeled one is.**

```
✗  The fix is deployed.

✓  VERIFIED — live on the containerized services (CD run <link>).
   ASSUMED, and in fact false — the host-level agent has a separate deploy path
   this run never touches; it still runs the old code until a manual redeploy.
```

The second version tells the reader exactly what remains. The first leaves a revoked assumption
lying around for the next session to cite as fact.

**Calibrate.** Uniform hedging destroys the signal: when every sentence carries a caveat, no caveat
carries information. Be firm where verified, loud where genuinely uncertain, and delete the silent
hedges in between.

---

## 2. The stamp — for claims that outlive the session

Any claim that will be cited later, or acted on by someone who wasn't there, carries:

```
<claim> · STATUS: CANDIDATE | VALIDATED | REJECTED · evidence: <path>
```

| Status | Means |
|---|---|
| `CANDIDATE` | Plausible, not established. **The default.** |
| `VALIDATED` | Reproducible from the cited evidence by someone who wasn't there. |
| `REJECTED` | Tested and failed. **Keep these** — a killed hypothesis is a result, and the next agent will otherwise re-run it. |

Add `NOT_COMPUTED` where a figure is genuinely unavailable. **Never substitute an estimate for a
number you could not compute** — an estimate that enters the record as a measurement is nearly
impossible to remove later.

**Rules.**

- **The evidence path is not optional.** A claim with no evidence path is not actionable —
  including the agent's own.
- **Default to `CANDIDATE`.** Promotion to `VALIDATED` is a deliberate act with a reproducible
  artifact behind it, not the natural drift of a claim that nobody challenged.
- **Keep the grammar greppable.** The literal words `STATUS:` and `evidence:` mean you can audit
  every claim in the repo with one search — and a linter can enforce that the value is one of the
  three (`scripts/review_zero.py` does exactly this).

---

## 3. Units and the recompute rule

Two rules that catch a disproportionate share of real errors.

**State the unit, always.** Percentile `[0,1]` vs. percent `[0,100]`; minutes vs. intervals;
fraction vs. basis points. Assert units at config-load or boot so a wrong-unit value **fails loudly
rather than silently disabling the rule it was meant to configure.**

**Recompute by a different path.** For any number you are about to publish, derive it a second way
— dimensional analysis, an order-of-magnitude bound, an independent query. Agreement between two
paths is real evidence; agreement between a number and your expectation is not.

> A dimensionless ratio arrived in one system reading `145.56`. Its plausible range is single
> digits, because it is a ratio of two like quantities. One line of dimensional reasoning exposed a
> unit mix in the producing code — the true value was `1.46`. Nobody needed to know the right
> answer in advance; they needed to ask **what the units must be.**

---

## 4. Naming what a result does *not* establish

The most valuable line in most findings. Make it a habit to write it explicitly:

- **Not a controlled comparison** — name the confound rather than hoping the reader spots it.
- **Not reproducible from the committed artifacts** — then the conclusion stays `CANDIDATE`, no
  matter how confident you are.
- **Measured under conditions X, may not transfer to Y** — sign and ordering sometimes carry when
  magnitudes don't; say which.
- **Absence of a signal is not a negative result** if the mechanism producing it was never
  active. *"Zero occurrences means the check never bound, not that it found nothing"* is a
  distinction that has saved entire analyses from being read backwards.

**Write against your own interest.** An agent that only records the flattering half of a result
produces a knowledge base that is confidently wrong — the most expensive kind.
