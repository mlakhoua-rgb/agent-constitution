# Contributing

This framework was extracted from one production system, not assembled from best-practice
articles — that is both its value and its bias. Contributions are welcome on either side of that
trade: evidence that something here works elsewhere, and evidence that it doesn't.

## The bar for additions

Every mechanism in this repo must **name the silent failure it prevents.** That is the selection
criterion the whole framework runs on, and it applies to the framework itself: a proposed check,
rule, or template section that cannot name its failure will be declined no matter how standard it
is elsewhere. Deletions are held to the mirror standard — show that a rule can no longer name the
failure it prevents, and removing it is a contribution, not a loss.

## What is most useful

- **Field reports.** You adopted a stage of this and something broke, chafed, or quietly stopped
  being load-bearing. An Issue with the specifics — what you adopted, what happened, what you
  changed — is worth more than a patch, because it is evidence the docs can cite.
- **Fixes with evidence.** A script defect with a reproduction, a claim that is wrong at its cited
  source, a gap between what [`ADOPTION.md`](ADOPTION.md) promises and what a fresh clone does.
- **Generalizations that subtract.** The templates still carry residue of the system they came
  from. A change that makes one more portable *by removing something* is usually right; a change
  that adds a knob usually isn't.

## This repo runs its own gates

PRs here go through the same machinery the repo ships:

- **Regression tests** run first (`python -m unittest discover -s tests -v`). Any bug fix to an
  executable governance claim should arrive with the smallest test that would have caught it.
- **review-zero** then runs on every PR. Added-line checks catch malformed new stamps, links,
  citations and migration defects. Impact-aware checks additionally inspect existing inbound
  references when a PR deletes, renames, or shrinks a target, so deletion-only diffs cannot create
  silent documentation breakage. Run `python scripts/review_zero.py` locally before pushing.
- **state-guard** requires every PR to touch `docs/STATE.md` or carry the `state:no-change`
  label. For most PRs here the label is the honest answer; a maintainer applies it in triage, so
  you don't need label permissions — just say in the PR body that project state is unchanged.
- The PR template's **Round-0 checklist and one-sentence risk statement** are to be filled in,
  not deleted. For docs PRs too: "no runtime verification" never means "claims need no evidence."
- **If your change touches a file adopters copy, add a `[Unreleased]` entry to
  [`CHANGELOG.md`](CHANGELOG.md) naming those files.** Adopters have no dependency on this repo;
  the release notes are the only thing that ever tells them a file they hold is now wrong.

The reference scripts support **Python 3.10+** and use the standard library only. GitHub Actions
currently exercises them on Python 3.11; compatibility changes should keep the documented floor
or change it explicitly with tests.

## Style

Match the voice: compressed, rationale-forward, every rule paired with the failure it prevents.
No marketing language. Wrap prose near 100 columns. American spelling.
