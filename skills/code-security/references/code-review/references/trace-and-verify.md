# Security Code Review

Use this procedure while reviewing a sensitive change or validating a reported vulnerability. Start with the requested boundary and widen only when callers, shared controls, or a confirmed root cause require it.

## Trace

1. **Record existing authority**: name the protected asset, the legitimate operation, and the attacker capability. Intentional administrator or autonomous-agent privileges alone do not establish privilege escalation.
1. **Find the actual enforcement**: read the entry point, callers, and effective configuration, including error, retry, cache, and alternate paths. A validator's name, a type annotation, or a prompt instruction does not prove enforcement.
1. **Contain derived-path writes**: before a delete or overwrite on a derived path, require the resolved target to sit below an allowlisted root (never the root itself) with ownership evidence beyond a marker file, and stop on refusal instead of falling back to a broader path.

## Verify

Write a falsifiable claim with its preconditions, and confirm it only with a reproducer, a failing fixture, or an isolated proof; also try a nearby case the control should reject. Classify each candidate as **confirmed** (reachable control failure with concrete impact), **refuted**, or **unresolved** (for example, reproduction blocked by missing credentials). Reuse the current authority for local fixtures; new external targets or effects need their own scope.

For an authorized fix, add a regression at the public boundary that fails before the fix, and check that legitimate operations still succeed. Fix the shared enforcing boundary rather than adding the same check to every caller. Then search for variants of the root cause with `rg` or `ast-grep`, after confirming the search finds the known case; a zero-result search counts only with its pattern and scope.

## Evidence

Report revision, path and line, actor and preconditions, input-to-operation trace, observed impact, reproduction, contrary evidence, confidence, and the smallest correction. [full-review](../../../../full-review/SKILL.md) owns severity and [threat-model](../../threat-model.md) owns architectural risk decisions.
