---
name: Truth gap (code ↔ configuration ↔ docs contradiction)
about: Open whenever two sources of truth disagree — CLAUDE.md §Sources of truth. One gap per issue.
title: "[truth-gap] "
labels: ["truth-gap"]
---

<!-- Consult order: deployed behavior → repository behavior → knowledge base. Answer the live
question from the layer authoritative for it. THIS ISSUE EXISTS SO THE DEVIATING LAYER GETS
CORRECTED DELIBERATELY, IN ITS OWN SESSION — never as a silent inline fix inside unrelated work.
That rule is the whole point: a contradiction quietly patched mid-task is a contradiction nobody
learns from, and it will reappear. -->

## The contradiction

One sentence: which layers disagree, about what.

## What each layer says (evidence required)

- **Deployed behavior** (live config / runtime state — include the command run):
- **Repository behavior** (`file:line` at the relevant revision):
- **Knowledge base** (doc § / state row / handoff path):

## Which layer is right, and why

Each layer wins its own question: code = behavior, configuration = live state, docs = intent and
decisions.

**If the *higher-authority* layer is the deviant one** — code contradicts a recorded Owner
decision, or live config contradicts what the code requires — say so explicitly. That is a **bug or
a broken state**, not a doc fix, and mislabeling it as a doc fix is how the underlying defect
survives.

## How to close the gap

Concrete fix + where it lands: doc edit / config change / code PR. Note anything that must stay
fail-closed or config-gated.

## Discovered during

Session / PR / task where the gap surfaced (link), so the closing session has the context.
