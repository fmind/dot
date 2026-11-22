# Whole-Repo Audit Dimensions and Rules

Supporting checklists for [Full Review](../SKILL.md).

## Dimension Checks

- **Works**: tasks and CLIs exit zero ([smoke](smoke.md)); failure, boundary, and race tests pass; authorized endpoints respond.
- **Current & Simple**: upgrade outdated deps on request ([upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md)); flag cohesive-boundary bloat (`~500` LOC/module guideline, never artificial splits) plus net LOC, flag, and dependency creep. Hunt dead code (`uvx vulture src tests --exclude '*/.venv/*' --ignore-decorators '@*_validator,@*.command,@*.callback'`), structural clones (`ast-grep`), orphan files, stale configs, and prose bloat ([trim](../../skillify/references/trim.md), `vale`).
- **Consistent & Secure**: align versions, metadata, [repo settings](../../github/references/repository/GUIDE.md), and [bootstrap](../../github/references/bootstrap.md); wire CI/hooks via [mise](../../mise/SKILL.md); audit ignores ([update-ignores](update-ignores/GUIDE.md)); scan secrets/deps (`code-security`, `sonar analyze`); sync [docs](../../docs/references/repository/GUIDE.md) and fix bottlenecks ([performance](../../python/references/performance.md)).

## Concurrency & Incident Rules

- **Concurrency & scale**: state expected/assumed load; check TOCTOU races, unshared in-process state, N+1 queries, and unbounded growth; never add layers, flags, or docs heavier than the fix.
- **Live incidents**: preserve evidence before containment, confirm authority before rotating, disclosing, or mutating production, prefer reversible mitigations, and leave external comms and ETAs to the owner.
