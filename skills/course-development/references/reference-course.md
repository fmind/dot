# Reference Course Profile

Use this profile only for a course that explicitly adopts the AgentOps reference course conventions. Its repository-local AGENTS.md owns the current schema and task names.

## Workflow

1. **Define the learner**: state prerequisites, target capability, available time, delivery platform, and accessibility constraints; cut content that does not advance the capability.
1. **Write observable outcomes**: give each page one primary outcome and a completion signal; closing bullets state what the learner can now do, name, or predict, never attendance.
1. **Frame every page**: follow [page](page.md): front matter with an explicit lowercase `slug` (plus `aliases` for any previously served URL), an "In one glance" abstract (You will / You need / Time), H2s that name their teaching purpose, `## Your turn` with the seven exercise fields, and `## What you can do now` ending in a `Continue to` link.
1. **Mirror the source**: include named regions from the shipped Python implementation using the project's documentation tooling; paste command output verbatim in `text` blocks, and derive every quoted count from a generated manifest (`data/captures.yaml` via `mise run docs:captures` in the reference course).
1. **Make labs executable**: state a prediction before the exercise, then declare the Mode (`inspect`, `temporary experiment` with target-specific preflight and cleanup, or `keep`), a preflight command, ordered steps, the gate command that proves completion, and the final state; label offline, live-model, container, Kubernetes, cloud, destructive, and paid commands.
1. **Explain diagrams**: follow every [mermaid](../../mermaid/SKILL.md) diagram with `**Diagram in words:**` prose; define terms at first use and put the reason beside each command.
1. **Check the human surface**: verify navigation, reading order, keyboard use, contrast, alt text, mobile layout, and copy-paste on rendered pages with playwright, then run the course's accessibility gate (`mise run check:accessibility` in the reference course).
1. **Validate progressively**: run the docs and link gates on the changed page first (`mise run check:docs` and `mise run check:links`), then the learner gate from a clean clone (`mise run install`, `mise run doctor`, `mise run check:core`, `mise run test`), then the definition of done in the course's `AGENTS.md`.
1. **Prepare release acceptance**: record the exact candidate, supported platforms, test evidence, known limitations, and correction path, and report the highest proven rung of the [proof ladder](../../production-readiness/SKILL.md); publishing remains a separate authorization.

## Conventions

- **Pages grow**: a rewrite that adds a definition pays for it by cutting tease, restatement, and asides.
- **Prerequisite creep**: `You need` declares machine state as the command that produces it (`mise run install` done), never "Chapter N finished".
- **Frozen routes**: a published slug never changes; a route change records the old address in the course's released-URL ledger or fails the build.
- **Scene headings**: an H2 names its technical subject and purpose, never a persona, a clock time, or a riddle.
- **Optional exercises**: keep them inline with a bold `**Optional exercise:**` label so they stay out of the sidebar.
