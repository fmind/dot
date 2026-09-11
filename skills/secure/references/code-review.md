# Security Code Review

Use this procedure while designing a sensitive change, reviewing its implementation, or validating a reported vulnerability. Start with the requested boundary and widen only when callers, shared controls, or a confirmed root cause require it.

## Trace the security decision

1. Identify the protected asset, legitimate operation, and attacker capability. Record what authority the actor already has; intentional administrator or autonomous-agent privileges alone do not establish privilege escalation.
1. Read the entry point, relevant callers, validation, and final operation. Record the concrete values and identities that cross each boundary, including tenant, resource owner, file path, destination, and execution principal.
1. Locate the enforcing code and effective configuration. Follow error paths, retries, caching, and alternate entry points. A validator's name, type annotation, or prompt instruction does not prove enforcement.
1. For a changed check, inspect the previous behavior and relevant history. Identify affected callers and whether the same test distinguishes the old and new behavior; avoid assigning severity from diff size or caller count alone.

| Boundary | Questions that change implementation or verification |
| --- | --- |
| Authorization | Is access checked against the requested object and tenant at the operation, including bulk, background, and cached paths? Can a supplied identifier select another user's resource? |
| Queries and subprocesses | Does untrusted data reach SQL syntax, a shell, an executable name, or command options? Parameter binding and argv lists address different injection mechanisms. |
| URLs and redirects | Which hosts, schemes, resolved addresses, and redirect destinations are reachable? Does the HTTP client preserve the intended destination restriction? |
| Files and archives | Do normalization, symlinks, extraction, and concurrent replacement preserve containment? Check the file actually opened, not only an earlier path check. |
| Serialization and templates | Can data select executable deserializers, template source, imports, or model loading code? Prefer a data-only format where the contract permits it. |
| Configuration | What do missing, empty, zero, negative, malformed, and conflicting values mean? Trace defaults and overrides to the actual security decision, distinguishing examples from reachable runtime values. |
| Logging and output | Can secrets, customer data, exception context, or model traces reach logs, HTML, terminals, or external telemetry? Does output escaping match its consumer? |
| Resource use | Are input size, expansion, concurrency, retries, time, and cost bounded at the owner of the operation? Can cancellation leave work or authority active? |

## Verify a suspected finding

Write a falsifiable claim with its preconditions. Try both the triggering case and a nearby case that the existing control should reject. Check framework guarantees and upstream validation before concluding that a dangerous-looking operation is exploitable. Conversely, do not invent a mitigating control you have not read or exercised.

Classify each candidate as **confirmed**, **refuted**, or **unresolved**. A confirmed finding needs a reachable control failure and concrete impact; a failed reproduction with missing credentials or environment is unresolved. Keep code defects, defense-in-depth gaps, and deliberate policy trade-offs distinguishable. Reuse the current authority for local fixtures and scoped execution; new external targets or effects require their own scope.

For an authorized fix, add a regression at the public boundary and prove it fails before the fix. Verify legitimate operations still succeed. Prefer correcting the shared enforcing boundary over adding equivalent checks independently to every caller.

## Search for related defects

Describe the confirmed root cause without its incidental variable names. Use `rg` for names and text, or [ast-grep](../../ast-grep/SKILL.md) when Python syntax is the useful discriminator. Verify the search finds the known case, then vary one relevant feature at a time: another entry point, equivalent API, data type, or configuration source. Search the agreed repository scope, not just the first affected module.

Review every candidate against its own callers and controls. Keep a compact record of confirmed instances, rejected lookalikes, unresolved candidates, and excluded paths. Stop expanding when additional patterns no longer represent the root cause; a zero-result search is meaningful only with its tested pattern and scope.

## Evidence

Report revision, path and line, actor and preconditions, input-to-operation trace, observed impact, reproduction, contrary evidence, confidence, and smallest correction. For implementation, include the regression and its result. [diff-review](../../diff-review/SKILL.md) owns severity and [threat-model](../../threat-model/SKILL.md) owns architectural risk decisions.
