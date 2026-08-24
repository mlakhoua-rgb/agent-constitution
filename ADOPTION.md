# Adoption — what to add, in what order, and what to skip

**Do not install all of this at once.** Every mechanism here is overhead, and overhead that
isn't paying for itself gets routed around within a month — after which the *documents* become
untrustworthy too, because everyone knows they're not really maintained.

Adopt in stages. Each stage is useful on its own and earns the next one.

---

## First: is this worth it for you?

The overhead pays for itself above a threshold. Roughly:

| Signal | Adopt |
|---|---|
| One agent, one person, reversible changes | **No.** Use a good README. Most of this is pure cost. |
| Multiple agents *or* multiple sessions per week on the same codebase | Stage 1 |
| A defect can cost money, data, or trust — and can fail *silently* | Stages 1–2 |
| Multiple agent vendors reviewing each other's work | Stages 1–3 |
| Agents merging with limited human review | All stages, and mean it |

The strongest single predictor is **silent failure**. If your system announces its own breakage
loudly and rollback is cheap, you need much less of this than someone whose worst outcome is code
that keeps running while quietly doing the wrong thing.

---

## Stage 1 — Constitution + decision log

**Files:** `CLAUDE.md`, `AGENTS.md`, `docs/DECISIONS.md`, `.github/ISSUE_TEMPLATE/`, `scripts/`

The highest value-to-effort ratio in the whole framework. An afternoon of work.

1. Copy `CLAUDE.md`, fill the `<PLACEHOLDERS>`. **Keep it under ~150 lines.** Length is what kills
   a constitution: past a certain size agents skim it, and a skimmed rule is not a rule.
2. Copy `AGENTS.md` and any other entry-point filenames your tools look for
   (`.github/copilot-instructions.md`, `GEMINI.md`, `.cursorrules`). **Make every one of them a
   three-line pointer** at the canonical file. Never a copy — copies drift, and an agent will
   confidently cite the stale one.
3. Start `docs/DECISIONS.md` with your **next real decision**.
4. Copy `.github/ISSUE_TEMPLATE/` and **create the label its truth-gap template names** — the
   constitution's "record a `truth-gap` Issue" rule depends on that label being findable, and a
   template label that doesn't exist in the repo is silently not applied. VERIFIED, and stamped so
   you can re-check it if GitHub's behavior changes: labels must already exist in the repository
   to be added · STATUS: VALIDATED · evidence:
   [GitHub's issue-template syntax docs](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms).

   ```bash
   gh label create truth-gap --color B60205 --description "Two sources of truth disagree"
   ```

5. Copy `scripts/` now, even though its stages come later. `session_brief.py` and
   `review_zero.py` are standalone and useful from day one; only `librarian.py` expects Stage 4's
   `STATE.md`. The alternative — a constitution citing scripts that aren't in the tree — is a
   broken citation in the one document every agent reads first.

> **Do not backfill decision history.** It will be reconstructed wrong — from memory, from commit
> messages, from what feels like it must have happened — and then cited as fact by every agent
> after you. An empty log that grows honestly beats a rich one that is quietly fictional.

**The one rule that makes or breaks this stage:** the decision entry lands in the *same PR* as the
change that implements it. A log maintained as a separate chore stops being maintained.

---

## Stage 2 — The craft layer

**Files:** `docs/reference/agent-operating-manual.md`, `docs/reference/evidence-grammar.md`

No CI, no tooling — just documents your agents read. This is where most of the quality improvement
actually comes from, and teams consistently underestimate it because it doesn't look like
infrastructure.

**Adapt the examples.** The manual's power is that every section carries a concrete worked example
from a real incident. Ship it with the placeholder examples and it degrades into generic advice
nobody applies under pressure. Replace them with your own incidents as you accumulate them —
*this file should be the most-edited document in your repo.*

Start enforcing two habits immediately, because they cost nothing and change everything:

- **VERIFIED / INFERRED / ASSUMED labels** on claims in agent output.
- **"The riskiest claim in this work is ___"** — one sentence, every deliverable.

---

## Stage 3 — The review contract

**Files:** `docs/reference/review-contract.md`, `.github/agent-review-guidelines.md`,
`.github/PULL_REQUEST_TEMPLATE.md`, `scripts/review_zero.py`, `.github/workflows/review-zero.yml`

1. **Write your standing invariants from your own incident history.** Do not adopt the shipped list
   wholesale. An invariant list assembled from best-practice articles will be long, generic, and
   ignored. The selection criterion is: *this has caused, or nearly caused, a real incident here.*
   Five invariants you can defend beat twenty you copied.
2. **Turn on the verdict stamp before anything else.** It is one line of reviewer instruction and
   it immediately fixes the worst ambiguity in automated review: silence and approval currently
   look identical.
3. **Mine `review_zero.py`'s check list from your own merged PRs.** Read your review threads, find
   the findings that repeat, script the ones that are *decidable*. The shipped checks are a
   starting set, not the answer.
4. **Adopt the iteration budget and the round-4 tripwire.** Cheap, and it catches the single most
   expensive agentic-review failure: a 40-comment thread converging on nothing because both parties
   are patching symptoms of a bad decomposition.

> **Do not skip the blast-radius rule.** Every mechanical check must run on **added lines only**.
> Without it, adding a check retroactively fails every open PR sitting near old code — and the
> team disables the check within a week.

---

## Stage 4 — Generated state

**Files:** `docs/STATE.md`, `scripts/session_brief.py`, `scripts/librarian.py`,
`.github/workflows/state-guard.yml`

The most machinery, and worth it only once you genuinely have parallel workstreams that agents keep
losing track of.

1. Add `docs/STATE.md` and start using it. **Give it two weeks before adding the guard** — a CI
   gate on a doc nobody has internalized just produces label-spam.
2. Wire `scripts/session_brief.py` as the session-start command in your constitution. Change the
   instruction from "read STATE.md first" to "run session_brief first" — that swap is the whole
   point of the stage.
3. Run `scripts/librarian.py --check` on a daily schedule. Route its output somewhere a human
   actually sees.
4. Add `state-guard.yml` **last** — and create its escape-hatch label first:

   ```bash
   gh label create state:no-change --color ededed --description "This PR changes no project state"
   ```

   The gate's pass path for a no-state-change PR *is* that label. A gate whose escape hatch
   doesn't exist fails closed with no documented way out — for every PR, including the ones that
   genuinely change nothing — and a gate like that gets disabled within a week.

> **Expected on a fresh clone:** `librarian.py --check` exits non-zero, reporting that §NOW,
> §NEXT, and §ACTIVE WORKSTREAMS carry no `as-of:` stamp. That is the tool working — the shipped
> `STATE.md` has `<YYYY-MM-DD>` placeholders, and an unstamped section is exactly what it is
> designed to flag. Replace the placeholders with real dates and it goes green.

---

## Things that look optional and are not

**The append-only decision log.** The moment you rewrite an entry, the log stops being history and
starts being marketing, and everyone correctly begins ignoring it.

**The verdict stamp on clean reviews.** Without it you cannot distinguish "reviewed, nothing found"
from "the reviewer crashed," and you will eventually merge on the second one.

**"A well-evidenced author rebuttal closes a thread."** Without it, a confidently wrong reviewer
holds correct PRs hostage, and authors learn to comply rather than argue. That's a much worse
failure than the occasional bad rebuttal.

**"Review the code that is there, not the code you would have written."** A reviewer that taxes
novelty trains the author out of it — and the whole reason to use capable agents is the work you
wouldn't have thought of.

**Stating absences explicitly.** When a tool is unavailable, the output must say so rather than
silently omitting the section. An agent must be able to tell "there are no open PRs" from "I
couldn't look." This one rule prevents a large class of confident-falsehood failures.

---

## Things to drop without guilt

- **The size and TTL budgets**, until a doc actually gets unwieldy. Premature budgets are noise.
- **The orphan report**, for small doc sets. It matters at 50+ documents.
- **Service-scoped constitutions**, until one service genuinely needs rules the others don't.
- **Formal severity tags (`[P0]`–`[P3]`)**, for a small team — but keep the *priority ordering*,
  which is the part that carries the information.

---

## The failure mode to watch for

**Governance theater** — the checklists get ticked, the stamps get applied, and none of it is
load-bearing any more. The tell is that nothing ever *fails*: no red CI, no rejected claim, no
decision entry that admits something didn't work.

The counter is the amendment rule, applied honestly: **a rule that can no longer name the failure
it prevents should be deleted.** Reread your invariant list every few months and cut the ones you
cannot attach to a real incident. A shorter list that everyone follows beats a longer one everyone
skims.
