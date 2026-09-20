# Audit Coverage and Finding Records

Use for broad or repeated source audits where findings alone cannot explain what was checked. Keep a small table in the response for a short audit; use the owning guide's optional JSON template when the task benefits from retained records. Do not create artifacts merely because this reference was loaded. Keep retained evidence in the assessment project or an agreed external directory; disposable work belongs in OS temporary space.

## Track coverage

1. Record the revision, relevant dirty changes, in-scope paths and boundaries, exclusions, and any time or execution limits. Reuse the task's authorization; this procedure does not authorize live probes or target-code execution.
1. Create one unit per meaningful entry point and trust boundary, splitting alternate enforcement paths when they need different checks. Give it a stable ID based on source symbols or route identities, not line numbers, reviewer, status, or severity. Avoid a Cartesian product of every file and attack category.
1. For each unit retain reviewed paths, checks and their results, evidence references, linked finding IDs, and a status: `planned`, `covered`, `blocked`, `deferred`, or `excluded`. A blocked unit has partial evidence and an exact blocker; deferred work has not been checked; exclusions need a scope reason. A covered unit needs actual checks and no outstanding verification gap. It can contain a confirmed finding: covered means examined, not safe.
1. Compare previous records against current callers, controls, configuration, and evidence before reuse. Reopen affected units when these change; a matching repository revision alone does not establish unchanged deployed conditions. Keep prior blocked or deferred work visible. Preserve superseded evidence separately with its original revision.

## Challenge coverage separately

After validating findings, review the coverage claim itself. Look for missing entry points, alternate routes to the same operation, background/retry paths, lifecycle transitions, unsupported exclusions, and unresolved earlier leads. Check the strongest enforcing control on each path. Reopen unsupported coverage and record newly discovered work; do not turn a coverage gap into a vulnerability.

Use a fresh reviewer when independent review or delegation is authorized. Otherwise perform a separate pass and state that it was not independent. Bound the pass by the agreed scope and budget, reserving time for verification and reporting before expanding investigation. At the limit, preserve partial evidence, mark untouched work deferred, and report partial coverage. Reviewer agreement or an empty findings list does not prove exhaustive coverage.

## Keep findings stable

Use the existing `confirmed`, `refuted`, and `unresolved` verdicts. Give each root cause a stable ID tied to its source control; multiple entry paths through the same defect share one record, while independent failed controls remain separate. Moving lines or changing verdicts must not change that identity.

Every record names its coverage units, actor, prerequisites, claimed boundary failure, ordered input-to-operation trace, evidence, and contrary evidence. Add verdict-specific information:

- **Confirmed**: observed result, demonstrated impact, severity, confidence, and the smallest correction with a regression plan. Verification follows the owning guide's trace-and-verify procedure.
- **Unresolved**: the exact fact preventing a verdict and the safe next check that could resolve it. Omit severity; prioritize verification separately without presenting the hypothesis as a vulnerability.
- **Refuted**: the control, result, or impossible prerequisite that disproves the claim. Retain the reason to avoid repeating it; changed evidence can reopen the same claim, and one refuted claim does not close its entire coverage unit.

Generate the summary from the final records. Check unique IDs, valid coverage links, required verdict evidence, and agreement between prose and records. Mark the coverage review `done` after its separate pass. Set `run_status` to `complete` only when in-scope checks and finding verification are finished; otherwise use `partial` and list the remaining work. Completion is relative to the declared scope, never proof of exhaustive security. JSON parsing checks syntax only; source traces and observations establish truth. Redact secrets and private payloads from retained examples.

## Provenance and scope

Reviewed [Cloudflare security-audit-skill at c1c8a8c](https://github.com/cloudflare/security-audit-skill/tree/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8) on 2026-09-20. These independently authored instructions incorporate coverage accounting, separate coverage review, and stable finding records into the existing workflow. No upstream scripts, schemas, or prose are vendored. The upstream [MIT license](https://github.com/cloudflare/security-audit-skill/blob/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/LICENSE) requires its notice when copying substantial portions. Full orchestration, custom validators, sandbox infrastructure, and the complete attack library remain outside this incorporation.
