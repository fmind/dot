# Repository Audit Procedure

Use for a whole-repository or cross-cutting audit; shared evidence, severity, and authorization rules live in [repository-review](../SKILL.md).

1. **Map the system**: inspect manifests, entry points, package boundaries, tasks, hooks, workflows, deployment and release automation, docs, generated files, and runtime configuration against the [review matrix](review-matrix.md). Keep the requested dimensions explicit.
1. **Check consistency**: compare documentation and public claims with current source, CLI metadata, task definitions, and generated output; prose alone does not establish behavior.
1. **Select evidence**: run focused checks that establish findings or resolve uncertainty. For explicit full qualification, run the project's full gate against the intended candidate; isolate mutating checks when unrelated work is present and avoid repeating already-passing checks.
1. **Inspect authorized live state**: distinguish local checks, hosted CI, publication, and runtime acceptance. Report the checked revision and exact unavailable boundary when credentials, services, or authorization are missing.
1. **Challenge conclusions**: reproduce high-impact claims safely and separate observed defects from speculative risk. A partial scan remains partial even when its completed checks pass.
1. **Report**: lead with ranked findings, then prioritized corrective actions and their required authority. For qualification requests, report the highest proven rung of the [proof ladder](../../production-readiness/SKILL.md), checks marked pass/fail/blocked/not run, and material gaps.
