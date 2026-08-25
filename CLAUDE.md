# <PROJECT NAME> — Agent Constitution

This is the repo-wide constitution for every coding agent (Claude, Codex, Gemini, Copilot, and
future ones). Keep it short, tool-neutral, and stable. It contains only routing, authority, and
non-negotiable rules; live state, runbooks, technical detail, evidence, and history belong in the
linked sources.

> **Filename note.** `CLAUDE.md` is canonical here because some tools auto-discover that filename;
> the **content and authority are vendor-neutral**. `AGENTS.md` and any other tool-specific entry
> points are thin pointers, never copies. Rename the canonical file only after verifying every
> target agent reliably follows the indirection.
>
> **Template note.** Everything in `<ANGLE BRACKETS>` is a placeholder. Delete this note when you
> adopt the file. Resist the urge to grow this document — length is what kills it. If it exceeds
> roughly 150 lines, something in it belongs in a reference doc instead.

## Start and orient

1. Run `date -u`, then `python scripts/session_brief.py`.
2. Read only the task-relevant sources in the map below. Before changing behavior, inspect the
   actual code, tests, schema, configuration, and artifacts; do not rely on prose alone.
3. When current repository behavior matters, fetch `origin/<DEFAULT BRANCH>` and identify the exact
   revision. When deployed behavior matters, verify the deployed revision and live configuration.
4. Do not ask the Owner to run a command an available agent can run. If this seat lacks access,
   hand the step to a capable seat; otherwise state the blocker plainly.

## Sources of truth

Ordered by authority. Each layer wins its own question.

- **Deployed behavior:** deployed revision + live configuration and runtime state.
- **Repository behavior:** code, tests, migrations, and schema at the relevant revision.
- **Intent and decisions:** `docs/DECISIONS.md`, then the relevant reference, then `docs/STATE.md`.
- **History:** `docs/archive/` is read-only and never current.

Resolve material contradictions from the authoritative layer, record a `truth-gap` Issue with
evidence, and tell the Owner. **Never silently work around a contradiction.** Minor documentation
defects may be fixed with the work when the risk is low and the correction is explicit.

## Authority and boundaries

Agents are trusted to investigate, choose methods, prototype, propose improvements, and implement
safe work without asking. **Prefer a recommendation backed by evidence over a menu of options.**

Do not change <THE CONSEQUENTIAL SURFACES OF YOUR SYSTEM — e.g. pricing, risk parameters, routing,
live/operator state, customer-facing copy> without the required evidence and authorization. Do not
take irreversible, outward-facing, paid, or third-party actions unless explicitly authorized.
Never merge on an unresolved review, failed CI, or branch conflict.

## Non-negotiable engineering rules

> Replace these with your own. Each rule below is here because it prevents a *silent* failure —
> that is the selection criterion. A rule that can no longer name the failure it prevents is a
> candidate for deletion.

- **Configuration is the runtime source of truth for <YOUR PARAMETER CLASS>.** Hot paths must never
  contain a default or silently fall back. Missing required configuration **fails closed** according
  to the owning service's documented contract.
- **Never weaken <YOUR PROTECTIVE GUARDS>.** Name them explicitly here so a diff touching one is
  self-evidently in scope for extra scrutiny.
- **Every migration has a working `downgrade()`**; do not create concurrent sibling migrations.
- **<YOUR RECURRING FOOTGUN>.** Every codebase has one or two type/serialization traps that have
  caused real incidents. Name them here with a pointer to the full contract.
- **Never hand-edit source on a production host.** Execute state-mutating remote operations
  sequentially and inspect each result before the next operation.

## Evidence rules

- Verify the primary source, the producing code, and an independent cross-check before stating a
  consequential result.
- Every consequential claim uses the stamp grammar:
  `<claim> · STATUS: CANDIDATE|VALIDATED|REJECTED · evidence: <path>`.
- Label **material claims** VERIFIED / INFERRED / ASSUMED in the deliverable itself. Ordinary
  connective prose does not need audit markup; the labels exist to make decision-relevant
  uncertainty visible, not to decorate every sentence.
- If a result is not reproducible, say so and keep the conclusion `STATUS: CANDIDATE`.

Full grammar: `docs/reference/evidence-grammar.md`.

## Delivery

Ship the smallest independently reviewable and revertible change justified by complexity and risk;
prefer small, fast, frequent PRs. Keep behaviorally distinct concerns separate. Low-risk adjacent
corrections may travel with the change **when explicitly identified**. All repository changes ship
by PR; never commit directly to `<DEFAULT BRANCH>`.

Before every push, run `python scripts/review_zero.py`, review the full diff as an adversary, and
run the relevant tests. Follow `docs/reference/review-contract.md`.

Update every document made stale by the change; record material decisions in `docs/DECISIONS.md`
without rewriting older entries, and preserve material findings outside chat.

**The author owns the PR through completion:** resolve every review finding, fix all required CI
failures, check mergeability and branch conflicts, and re-request review after each push.
Resolution means a fix **or** an evidence-backed rejection replied on the finding's own thread —
never silence. `<NAMED REVIEWER>` is the required reviewer for every PR, including PRs it authored
itself. Once required CI is green, the branch is conflict-free, every finding is resolved, and the
required reviewer gives a green light **on the latest commit**, the author may merge immediately.
**Never treat silence, an older review, or CI green alone as approval.**

## Knowledge map

| Need | Source |
|---|---|
| Session truth and freshness | `scripts/session_brief.py` |
| Durable decisions | `docs/DECISIONS.md` |
| Current intent and workstreams | `docs/STATE.md` |
| How to work / verification method | `docs/reference/agent-operating-manual.md` |
| Review gates and merge contract | `docs/reference/review-contract.md` |
| Claim and evidence grammar | `docs/reference/evidence-grammar.md` |
| <Platform runbooks> | `<docs/reference/platform-reference.md>` |
| Service-specific rules | `services/<service>/CLAUDE.md` |
| Session evidence | `docs/handoffs/<YYYY-MM-DD>-<topic>.md` |
| Backlog and truth gaps | `.github/ISSUE_TEMPLATE/` |

## Amending this document

Rules here change only with the Owner's approval and a new entry in `docs/DECISIONS.md`.
**Challenge a rule with evidence when its cost exceeds the failure it prevents** — that is part of
the job, not an escalation.

---

### Optional: legacy section-name compatibility

Once agents and issues start citing `CLAUDE.md §SomeSection` by name, renaming a section silently
breaks every citation. Keep a small table mapping old names to canonical ones rather than
forbidding renames:

| Existing citation | Canonical location |
|---|---|
| `<§OldName>` | `<§New canonical section>` |
