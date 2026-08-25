# Review Contract — gates, verdicts, and the merge decision

How a change gets from "an agent wrote it" to "it is on the default branch." Every rule here was
added because its absence caused a real problem.

---

## The shape of the pipeline

```
Round 0        author self-review, BEFORE the first push
   ├── mechanical:  tests + scripts/review_zero.py    (deterministic, scriptable)
   └── adversarial: full diff vs. standing invariants (judgment, not scriptable)
        ↓
Required CI   tests · lint · state-guard · review-zero
        ↓
Round 1..N    independent reviewer → author fixes → author replies on each thread
        ↓                                    ↑
        └────── re-request review of the LATEST commit ──┘
        ↓
Merge gate    CI green ∧ conflict-free ∧ every finding resolved
              ∧ reviewer green light ON THE LATEST COMMIT
```

---

## Round 0 — the author reviews their own diff first

**Before every push**, not just the first one.

The single highest-leverage change to review throughput is moving findings *earlier*. A finding
caught in Round 0 costs minutes; the same finding caught in Round 3 costs a full review cycle, a
context reload for both parties, and a re-request.

**The mechanical half** is the regression suite plus `scripts/review_zero.py`. The local semantic
checks are scoped to added lines so old debt cannot block unrelated work. Referential integrity is
scoped differently: when a PR deletes, renames, or shrinks a target, existing inbound links and
`path:line` citations to that impacted surface are checked across the repository. A deletion-only
PR therefore cannot return clean merely because it added no lines.

The check list should be **mined from your own merge history**: look at which findings your reviewers
actually burn rounds on, and script the ones that are decidable.

**The adversarial half cannot be scripted and is still mandatory.** Read your own full diff as
someone paid to reject it, against the standing invariants in
[`.github/agent-review-guidelines.md`](../../.github/agent-review-guidelines.md).

> **Blast-radius rule:** mechanical checks must not surface unrelated pre-existing debt. Added-line
> checks inspect what the PR introduces; impact checks inspect only references that the PR can
> invalidate. "Added lines only" is not a valid excuse for missing a broken inbound reference.

---

## Standing invariants

These live in [`.github/agent-review-guidelines.md`](../../.github/agent-review-guidelines.md) so
that automated reviewers read the same list a human does. **Tune the review by editing that file —
no CI change needed.** That property matters more than it sounds: a review rubric you have to ship
a workflow change to adjust is a rubric that stops being adjusted.

---

## Reviewer conduct

**Required.**

- **An independent reviewer on every PR** — including PRs authored by that reviewer's own vendor.
  Self-review plus green CI is not sufficient.
- **Post inline comments on the specific changed line** for concrete issues; a top-level comment
  for cross-cutting observations.
- **Severity-tag every finding:** `[P0]` broken/unsafe, must fix · `[P1]` likely bug/risk ·
  `[P2]` should fix · `[P3]` nit/optional. Fail-direction and data-integrity defects are P0/P1 by
  default.
- **Priority order:** correctness on the consequential path > fail-direction > data integrity >
  migration safety > tests > everything else.

**Forbidden.**

- **No style comments.** No formatting, naming-taste, or micro-performance nits. They crowd out
  real findings and train authors to optimize for the reviewer's taste.
- **No praise, no summary of what the PR does.** The author knows. It pads the thread and hides
  the findings.
- **Do not review the code you would have written.** An unfamiliar structure, a new abstraction, or
  an approach you would not have chosen is **not a finding** — say nothing unless you can name the
  input that makes it fail or the invariant it breaks.
- **Scope findings to the diff and its blast radius.** Pre-existing defects the PR merely sits near
  belong in an Issue. Flagging them here converts every PR into an unbounded audit.

---

## The verdict stamp — mandatory on every review, including clean ones

Every review ends with exactly one top-level verdict comment. **Including when the diff is clean.**

> **Why.** Without it, a clean PR is indistinguishable from a PR that nothing reviewed — the
> reviewer crashed, the workflow didn't trigger, the token expired. Silence and approval look
> identical, which forces a second reviewer just to confirm coverage.
>
> **Never manufacture findings to fill it.** "Clean" is a valid, common, and useful verdict.

First line must be exactly one of:

```
**<Reviewer> review — CLEAN**
**<Reviewer> review — N finding(s)**
```

Then one line naming **what you actually traced**. If not clean, list each finding as
`[P0]–[P3] <one line> → <link to its inline comment>`.

The stamp is the required audit trail; it is **not** the forbidden praise/summary, and it does not
replace the inline comments, which still carry the actual findings.

---

## Resolution — what closes a thread

**Every finding needs a commit plus a reply on its own thread** — what changed and in which commit,
or why it is deferred with a linked Issue. **Never silence.** Pushing a fix without replying is not
resolution: the reviewer cannot tell a fix from an oversight, and re-raises it next round.

**A well-evidenced author rebuttal resolves a finding for iteration accounting.** If the author
replies with the `file:line`, query, or reproducible artifact that refutes a finding, do not keep
re-raising the same finding without new evidence.

**That does not satisfy the independent-approval gate.** "Finding resolved" and "reviewer approved
the latest commit" are separate conditions. The author cannot manufacture the required green light
by declaring their own rebuttal sufficient.

**Re-request review of the latest commit after each fix push.** An approval on an older commit is
not an approval of what you are about to merge.

---

## The iteration budget and the round-4 tripwire

**Budget: ≤ 10 reviewer rounds per PR.** Track them in the PR body:

| round | findings | fixed in |
|---|---|---|
| 1 | 6 | `abc1234` |
| 2 | 4 | `def5678` |
| 3 | 5 | `9012abc` |

**The tripwire is at round 4 with a flat trend.** A finding count that is not *falling* by round 4
is not a quality problem — it is a **structural** one. The PR is too large, mixes concerns, or
rests on a premise nobody has checked. Iterating harder will not fix any of those.

*Response:* stop fixing findings. Decompose the PR, or go settle the premise.

---

## The merge gate

Merge only when **all** of these hold:

1. Required CI is green.
2. The branch is conflict-free against the default branch.
3. Every finding is resolved — a fix, or an evidence-backed rejection replied on its thread.
4. The required reviewer has given a green light **on the latest commit**.

**Never treat as approval:** silence · an older review · CI green alone · your own confidence · your
own rebuttal to a review finding.

> **On merge authority for agents.** Whether an agent may merge on its own is a per-project call
> that belongs in the constitution, not here. If you do grant it, grant it *conditionally* — bound
> to the four gates above and scoped to specific environments — and write the scope down.

---

## Docs and markdown PRs get the same rigor

Applied to **material claims** rather than runtime code. Flag:

- a consequential persisted claim missing the stamp grammar (`STATUS: … · evidence: <path>`)
- a dead cross-reference or a citation invalidated by a deleted, renamed, or shortened target
- a contradiction with the constitution or a reference doc
- a result labeled as validated when its evidence does not support it

A wrong doc is worse than a missing one, because it is *trusted*.
