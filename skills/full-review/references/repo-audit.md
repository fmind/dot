# Whole-Repo Audit Dimensions and Rules

Supporting checklists for [Full Review](../SKILL.md).

## Dimension Checks

- **Works**: tasks and CLIs exit zero ([smoke](smoke.md)); failure, boundary, and race tests pass; authorized endpoints respond.
- **Current & Simple**: upgrade outdated deps on request ([upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md)); flag cohesive-boundary bloat (`~500` LOC/module guideline, never artificial splits) plus net LOC, flag, and dependency creep. Hunt dead code (`UV_MALWARE_CHECK=1 uvx --preview-features malware-check 'vulture==2.16' src tests --exclude '*/.venv/*' --ignore-decorators '@*_validator,@*.command,@*.callback'`), structural clones (`ast-grep`), orphan files, stale configs, and prose bloat ([trim](../../skillify/references/trim.md), `vale`).
- **Consistent & Secure**: align versions, metadata, [repo settings](../../github/references/repository/GUIDE.md), and [bootstrap](../../github/references/bootstrap.md); wire CI/hooks via [mise](../../mise/SKILL.md); audit ignores ([update-ignores](update-ignores/GUIDE.md)); scan secrets/deps via [code-security](../../code-security/SKILL.md) and [sonarqube](../../code-security/references/sonarqube.md) (`sonar` is project-pinned); sync [docs](../../docs/references/repository/GUIDE.md) and fix bottlenecks ([performance](../../python/references/performance.md)).

## Structural Search (`ast-grep`)

Use `ast-grep` for syntax-aware searches and persistent invariant rules instead of brittle regexes:

- **Ad-hoc structural queries**: run `ast-grep run -p '<pattern>' <paths>` using `$A` for a single AST node and `$$$ARGS` for variadic nodes/arguments (e.g., `ast-grep run -p 'subprocess.run($$$ARGS, shell=True, $$$REST)' src/`).
- **Committed rule gates**: declare `ruleDirs` in `sgconfig.yml`, author YAML rules under `.ast-grep/rules/*.yml` with a remediation `message:`, and run `ast-grep scan` (and `ast-grep test` for rule fixtures) in CI.

## Concurrency & Incident Rules

- **Concurrency & scale**: state expected/assumed load; check TOCTOU races, unshared in-process state, N+1 queries, and unbounded growth; never add layers, flags, or docs heavier than the fix.
- **Live incidents**: delegate triage, containment, and postmortems to [sre](../../sre/SKILL.md).
