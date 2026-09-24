---
name: learning
description: "Update project notes, concepts and action folders after meaningful work."
---

# Keep knowledge current

Knowledge is Markdown in the brain; Git keeps its history. Keep each note short and current so the next session can act on it.

1. Find the owning note with `bf search`. Prefer updating it over creating a new one. Read it fully before editing.
1. Choose the place: a project's state, decisions and next actions in `projects/<project>.md`; reusable knowledge in `concepts/<concept>.md`; a delegated or multi-session job in `actions/YYYY-MM-DD_slug/ACTION.md` with `inputs/` and `outputs/`; a repeated procedure in the brain's `skills/`.
1. Edit in place. Replace outdated statements instead of appending history sections; add a dated one-line entry under `## Decisions` for each decision, with its reason and a ref to the evidence (`[meeting](source:id)`). Set `updated: YYYY-MM-DD`.
1. Only write what you verified or the user stated. Mark proposals as proposals. Never invent provenance, verification or dates.
1. Run `bf validate` and fix every broken link or missing record it reports. `bf status` lists active project notes due for `review` (not updated for 14 days); refresh one when you touch its project. Show the diff; commit only when the user's standing instructions allow it.

Project notes follow this shape:

```markdown
---
type: project
status: active # active | paused | blocked | done | archived
updated: 2026-09-22
summary: One sentence on what this project is for.
aliases: [repo:github.com/owner/name]
---

# Project

Intent in two or three sentences.

## Now

Current state in a short paragraph, with links to canonical documents or repositories.

## Decisions

- 2026-09-22: decision, because reason ([evidence](source:id)).

## Next actions

- [ ] The single most important next step.
```

Concepts follow OKF v0.2 (see the Brain Framework repository's `skills/bf-learn/templates/concept.md`): a `type`, `status: draft|stable|deprecated`, `sources` as mappings with a `resource`, and `verified` only for real checks with `by` and `at`. Keep `concepts/index.md` a short list of entry points. Actions start from the Brain Framework repository's `skills/bf-learn/templates/action.md` and keep a Resume section with the exact next action.

After substantial work, recommend one concrete update to the user when it would save a future session time: what to change, where, and why.
