# Security Code Review

Review sensitive changes or suspected vulnerabilities at the requested boundary, widening only when callers, shared controls, or root causes require it.

## Trace

1. **Establish authority**: name asset, legitimate operation, and attacker capability (intentional admin or autonomous-agent permissions are not privilege escalation).
1. **Locate real enforcement**: trace entry points, callers, config, and error/retry/cache/alternate paths—names, type hints, and prompts are not controls.
1. **Bound derived-path writes**: before deleting or overwriting a derived path, verify the resolved path sits strictly inside (never equal to) an allowlisted root with ownership proof beyond a marker file, and abort on refusal.

## Verify

Prove a falsifiable claim via reproducer, failing fixture, or isolated trace (plus a nearby rejected case) and label it **confirmed**, **refuted**, or **unresolved** (external targets require explicit scope). Fix the shared boundary with a failing-first public regression test, verify legitimate callers pass, and hunt variants via `rg` or `ast-grep` (confirming the query matches the known bug first).

## Evidence

Report revision, `path:line`, actor/preconditions, input-to-operation trace, impact, reproduction, contrary evidence, confidence, and minimal fix; [full-review](../../../../full-review/SKILL.md) owns severity and [threat-model](../../threat-model.md) owns design risk.
