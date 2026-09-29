---
name: learning
description: "Update project notes and concepts after meaningful work: OKF status, namespaced aliases, typed links, tasks and evals."
---

# Keep knowledge current

<!-- Mirrors github.com/fmind/brain-framework skills/bf-learn (v15.0.0); update it there first. -->

Knowledge is Markdown in the brain; Git keeps its history. Keep each owning note short and current so a future session can act on it. For a review-only request, report proposed edits instead.

1. Select the intended brain and audience, read its `AGENTS.md` and resolve its directory before filesystem edits. Run commands there or pass `--brain PATH`.
1. Find the owner with `bf search "project or topic"` and read it fully. Project state, decisions and next actions go in `projects/`; reusable knowledge in `concepts/`; session detail in an existing action (create one only when asked); shared media in `assets/`; repeated procedures in the brain's `skills/`.
1. Make focused edits that preserve unrelated paragraphs and stable anchors. Replace outdated current-state claims; keep consequential earlier rationales with their evidence. Record each decision with its reason and a supporting ref (`[meeting](source:id)`). Change `updated` only for meaningful content changes.
1. Write only what you verified or the user stated; mark proposals, unknowns and disputed evidence. When records disagree, compare revision time, observation time and collection coverage before replacing a claim. Never rewrite collected records to support a conclusion.
1. Run `bf validate` and fix problems introduced by the edit (each names its `file`); report unrelated failures without deleting evidence. Search the intended question and read the returned ref. When the answer must stay findable, add or update a case under `evals/` (a new suite starts with `version: 5`) and run `bf eval`. Show the changed refs, diff and remaining uncertainty; commit only within the user's standing authorization.

After substantial work, recommend one concrete update when it would save a future session time: what to change, where and why.

## Note format

Projects, concepts and `ACTION.md` notes are OKF: a nonempty `type`, `status: draft|stable|deprecated`, `sources` mappings with a `resource` (indexed as `cites` claims), and `verified` only for real checks with `by` and `at`. Status is note maturity, not work progress: keep progress in the body and task list. Only `deprecated` closes a note; set it only when the owner confirms the work is over.

```markdown
---
type: project
status: draft
updated: 2026-09-28
summary: One sentence on what this project is for.
aliases: [repo:github.com/owner/name]
---

# Project

Intent in two or three sentences.

## Now {#now}

Current state in a short paragraph, with links to canonical documents or repositories.

## Decision {#decision}

The current decision, because reason ([evidence](source:id)).

## Next actions {#next-actions}

- [ ] The single most important next step.
```

Follow the brain's `AGENTS.md` when it prescribes other headings, such as dated `## Decisions` entries. Write next steps as checkboxes in their owning note only: `bf read tasks` counts them, and copied checkboxes become duplicate tasks. Keep `concepts/index.md` a short list of entry points; concepts start from the [concept template](https://github.com/fmind/brain-framework/blob/v15.0.0/skills/bf-learn/templates/concept.md).

## Identities and links

- `aliases` hold verified namespaced identities (`scheme:value`), never display names; write GitHub repository identities in lowercase, as sensors emit them. A record ref such as `jira:PROJ-1` is already an identity: link to it instead of repeating it as an alias. Entities and aliases stay in this brain's namespace, and page paths (home, folder roots, `tasks`, periods, `tags/*`, `memories/*`) cannot be claimed.
- Only projects, concepts and `ACTION.md` notes declare `entity`, `aliases` and `tags`. Other Markdown, such as action inputs and outputs, is ordinary: only valid `title`, `type`, `status`, `updated`, `summary` and `description` apply, its typed links use the file as subject, and `entity`, `aliases`, `tags`, `sources` and review dates are ignored.
- Use stable `bf://<bf.yaml name>/...` addresses across brains; an OKF note may declare `entity: bf://NAME/people/ID`. Declare each role under `schema:` in `bf.yaml` (`type: identity`, `relation: true`) before writing `[label](bf://NAME/path?rel=ROLE#section)`; `bf init` declares `author`, `owner`, `depends-on` and `related-to`; `tagged-with`, `links` and `cites` are reserved. A role may declare one `broader` parent and allowed `targets` prefixes. The subject is the note entity, otherwise its file: to state another entity's relationship, write the link in that entity's note. `rel` is the only BF link query and precedes the fragment; percent-encode spaces and `%`. Keep authorship and ownership in named relationships, not URI userinfo.
- Relative links start from their file; in `projects/` and `concepts/`, a leading `/` starts from that folder. Use explicit heading anchors (`## Title {#stable-id}`) for durable section refs. `bf validate` reports foreign links under `unresolved` without opening them.
- Reuse topic labels from `bf read tags` (`tags: [agents, retrieval]`): exact, case-sensitive and brain-local. Never infer identity, relationships or tags from name similarity or provider labels.
- Related brains belong in `bf.yaml` as `brains: {team: {path: ../team}}`, with matching names and paths relative to the declaring root; references and registration never grant execution. Promote only reviewed, shareable summaries into a team brain, with evidence teammates can access.

Review reminders (`review_reasons`) follow local modification time, `review_after` or `review_due`: never touch a file merely to clear one or treat a recent edit as verification.
