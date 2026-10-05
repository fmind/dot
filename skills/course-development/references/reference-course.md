# Reference Course Profile

Use this profile only for a course that explicitly adopts the AgentOps reference course conventions. The course's [documentation workflow](https://github.com/MLOps-Courses/agentops-open-course/blob/main/AGENTS.md#documentation-workflow) owns the current page frame, schema, and task names, and its `mise run check:docs` enforces them; read it before writing a page.

## Workflow

Apply these deltas on top of the [course workflow](../SKILL.md#workflow); the learner definition, outcomes, and progressive validation stay there.

1. **Frame every page**: copy the frame from the course's documentation workflow: `description`-only front matter, an `!!! abstract "In one glance"` block (You will / You need / Time), question-style H2s, and the fixed closing H2 (`What proves this page worked?` on most pages) with its `**You are done when:**` list and a `Continue to` link. The closing verification states what the learner can now do, name, or predict, never attendance.
1. **Mirror the source**: include named regions from the shipped Python implementation using the project's documentation tooling; paste command output verbatim in `text` blocks, and regenerate quoted counts from the source instead of retyping them.
1. **Make labs executable**: state a prediction before the exercise, then declare the fields the course's convention checker enforces: the Mode (`inspect`, `temporary experiment` with a target-specific dirty-tree preflight and cleanup, `keep`, or `capstone carry-forward`), Goal, Files to touch, Preflight, the gate that proves completion, and the final state; label offline, live-model, container, Kubernetes, cloud, destructive, and paid commands.
1. **Explain diagrams**: follow every [mermaid](../../diagrams-as-code/references/mermaid.md) diagram with `**Diagram in words:**` prose; define terms at first use and put the reason beside each command.
1. **Run the course gates**: check rendered pages with playwright, then `mise run check:accessibility`; run `mise run check:docs` and `mise run check:links` on the changed page first, then the learner gate from a clean clone (`mise run install`, `mise run doctor`, `mise run check:core`, `mise run test`), then the definition of done in the course's `AGENTS.md`.
1. **Prepare release acceptance**: also record the exact candidate and supported platforms, and report the highest proven rung of the [proof ladder](../../production-readiness/SKILL.md); publishing remains a separate authorization.

## Conventions

- **Pay for additions by cutting**: a rewrite that adds a definition pays for it by cutting tease, restatement, and asides.
- **Declare prerequisites as machine state**: `You need` declares machine state as the command that produces it (`mise run install` done), never "Chapter N finished".
- **Record every route change**: a published route never changes silently; a route change records the old address in the course's released-URL manifest (`docs/released-urls.json`) or fails the build.
- **Use question headings**: every H2 asks the question its section answers and ends in `?`; never a persona, a clock time, or a riddle.
- **Keep optional depth off the main path**: keep optional exercises inline with a bold `**Optional exercise:**` label so they stay out of the sidebar; move valuable second-pass detail into `??? note "Deeper: …"` collapsibles.
