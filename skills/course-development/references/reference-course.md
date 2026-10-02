# Reference Course Profile

Use this profile only for a course that explicitly adopts the AgentOps reference course conventions. The course's [documentation workflow](https://github.com/MLOps-Courses/agentops-open-course/blob/main/AGENTS.md#documentation-workflow) owns the current page frame, schema, and task names, and its `mise run check:docs` enforces them; read it before writing a page.

## Workflow

1. **Define the learner**: state prerequisites, target capability, available time, delivery platform, and accessibility constraints; cut content that does not advance the capability.
1. **Write observable outcomes**: give each page one primary outcome and a completion signal; the closing verification states what the learner can now do, name, or predict, never attendance.
1. **Frame every page**: copy the frame from the course's documentation workflow: `description`-only front matter, an `!!! abstract "In one glance"` block (You will / You need / Time), question-style H2s, and the fixed closing H2 (`What proves this page worked?` on most pages) with its `**You are done when:**` list and a `Continue to` link.
1. **Mirror the source**: include named regions from the shipped Python implementation using the project's documentation tooling; paste command output verbatim in `text` blocks, and regenerate quoted counts from the source instead of retyping them.
1. **Make labs executable**: state a prediction before the exercise, then declare the fields the course's convention checker enforces: the Mode (`inspect`, `temporary experiment` with a target-specific dirty-tree preflight and cleanup, `keep`, or `capstone carry-forward`), Goal, Files to touch, Preflight, the gate that proves completion, and the final state; label offline, live-model, container, Kubernetes, cloud, destructive, and paid commands.
1. **Explain diagrams**: follow every [mermaid](../../diagrams-as-code/references/mermaid.md) diagram with `**Diagram in words:**` prose; define terms at first use and put the reason beside each command.
1. **Check the human surface**: verify navigation, reading order, keyboard use, contrast, alt text, mobile layout, and copy-paste on rendered pages with playwright, then run the course's accessibility gate (`mise run check:accessibility` in the reference course).
1. **Validate progressively**: run the docs and link gates on the changed page first (`mise run check:docs` and `mise run check:links`), then the learner gate from a clean clone (`mise run install`, `mise run doctor`, `mise run check:core`, `mise run test`), then the definition of done in the course's `AGENTS.md`.
1. **Prepare release acceptance**: record the exact candidate, supported platforms, test evidence, known limitations, and correction path, and report the highest proven rung of the [proof ladder](../../production-readiness/SKILL.md); publishing remains a separate authorization.

## Conventions

- **Pages grow**: a rewrite that adds a definition pays for it by cutting tease, restatement, and asides.
- **Prerequisite creep**: `You need` declares machine state as the command that produces it (`mise run install` done), never "Chapter N finished".
- **Frozen routes**: a published route never changes silently; a route change records the old address in the course's released-URL manifest (`docs/released-urls.json`) or fails the build.
- **Question headings**: every H2 asks the question its section answers and ends in `?`; never a persona, a clock time, or a riddle.
- **Optional depth**: keep optional exercises inline with a bold `**Optional exercise:**` label so they stay out of the sidebar; move valuable second-pass detail into `??? note "Deeper: …"` collapsibles.
