---
name: Backlog item
about: A unit of work. One concern per issue.
title: ""
labels: []
---

<!-- Add a priority:* and type:* label. An issue with no analysis attached is a to-do you handed to
your successor — if it was cheap to answer, answer it first and file the answer. -->

## The deliverable

What the requester will *use* when this is done: a decision, a diff, a number, a diagnosis.
**Not the activity** ("look into X") — the artifact.

## Why now

What is blocked or at risk while this is open. If nothing is, say so — that is useful and affects
priority honestly.

## Done condition

The check that proves it. If you cannot state the check, the item is not yet well-cut — split it
until every piece has its own pass/fail test that runs *without the other pieces existing*.

- [ ] <check>

## What is already known

Evidence gathered so far, with paths. Label each claim VERIFIED / INFERRED / ASSUMED.

## Out of scope

What this deliberately does not cover, so the PR stays reviewable and the next reader does not
re-litigate the boundary.
