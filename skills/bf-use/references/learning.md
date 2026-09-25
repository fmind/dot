---
name: learning
description: "Update project notes and concepts after meaningful work, with task lists pages can count."
---

# Keep knowledge current

<!-- Mirrors github.com/fmind/brain-framework skills/bf-learn/SKILL.md; update it there first. -->

Knowledge is Markdown in the brain; Git keeps its history. Keep each note short and current so the next session can act on it.

1. Select the intended brain and audience. Find the owning note with `bf search "project or topic" --brain NAME`. Prefer updating it over creating a new one. Read it fully before editing; resolve the brain path before using filesystem tools.
1. Choose the place: a project's state, decisions and next actions in `projects/<project>.md`; reusable knowledge in `concepts/<concept>.md`; one session of work the user asked to track as an action in `actions/YYYY-MM-DD_slug/ACTION.md` (see `bf-action`); media shared by several notes in `assets/`; a repeated procedure in the brain's `skills/`.
1. Edit in place. Replace outdated statements instead of appending history sections; add a dated one-line entry under `## Decisions` for each decision, with its reason and a ref to the evidence (`[meeting](source:id)`). Set `updated: YYYY-MM-DD`.
1. Only write what you verified or the user stated. Mark proposals as proposals. Never invent provenance, verification or dates.
1. When records disagree, compare upstream revision time, observation time and declared collection coverage; do not silently turn a partial or historical record into a current fact. Promote only reviewed, shareable summaries into a team brain, with evidence teammates can access.
1. Run `bf validate --brain NAME` and fix problems introduced by the edit; report unrelated failures without deleting evidence to pass a check. When the edit changes an answer the brain should retain, add or update its `evals/retrieval.yaml` case and run `bf eval --brain NAME`. `bf read projects` marks active or blocked project notes with `review` when they are older than 14 days or newer items link to them (`new_links`); read the project to see those backlinks and refresh its note from them. Show the diff; commit only when the user's standing instructions allow it.

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

Concepts follow OKF v0.2 ([template](https://github.com/fmind/brain-framework/blob/main/skills/bf-learn/templates/concept.md)): a `type`, `status: draft|stable|deprecated`, `sources` as mappings with a `resource`, and `verified` only for real checks with `by` and `at`. Keep `concepts/index.md` a short list of entry points. Actions follow the `bf-action` skill and keep a Resume section with the exact next action. Keep next actions as task list items (`- [ ]`) so pages count them and show the first open one.

Replace sample dates, identities and refs with verified values. Do not rewrite collected records to make a note true; update the authored interpretation and retain its evidence.

After substantial work, recommend one concrete update to the user when it would save a future session time: what to change, where, and why.

Shared field meanings, types, cardinality and examples live under `schema` in `bf.yaml`; sensor `fields` map explicit output paths or constants into them. Read an identity (`bf read IDENTITY`) to follow its typed relationships and read their supporting records. Keep technical checks in `tests/` and retrieval suites in `evals/`; `bf eval` runs all suites, while `--path evals/NAME.yaml` selects one.

## Portable links and relationships

Use stable `bf://<bf.yaml name>/...` addresses across brains. An authored note may declare `entity: bf://NAME/people/ID` (or another logical namespace), with verified alternate identities in `aliases`. Declare each role in `bf.yaml` (`type: identity`, `relation: true`) before writing `[label](bf://NAME/path?rel=ROLE#section)`. The subject defaults to the note entity, otherwise its file; use `subject=IDENTITY` when stating a relationship between other entities. Keep authorship and ownership in named relationship fields, not URI userinfo. Query values must be percent-encoded, and query attributes belong before the fragment. Other URI schemes retain their original query semantics.

`bf read IDENTITY` returns incoming links grouped by relationship under `backlinks` and claims with that explicit subject under `claims`. Read the returned `relations[].origin` and `evidence`; these retain the actual assertion and its cited support separately. Exact reads accept BF addresses. Use explicit heading anchors (`## Display title {#stable-id}`) when a section needs a durable ref. Keep the brain's `name` stable across clones. Selected-brain scope is a boundary: links never add another brain or contact a network. Ambiguous aliases and incomplete searches need review; `bf validate` reports foreign links under `unresolved` without opening them.

Related brains belong in `bf.yaml` as `brains: {team: {path: ../team}}`. Use stable matching names and paths relative to the declaring root. Search/read include direct references only; check `problems` before claiming absence. References never grant sensor execution permission.
