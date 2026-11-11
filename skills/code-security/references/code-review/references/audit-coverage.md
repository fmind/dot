# Audit Coverage and Finding Records

Use for broad or repeated source audits: inline a compact table for small passes, or use the parent guide's JSON template when retained records help (store retained evidence in-project or an agreed path, scratch work in OS temp).

## Track coverage

1. **Record scope and limits**: commit, dirty changes, in-scope paths/boundaries, exclusions, and time/execution caps (static review never authorizes live probes or target execution).
1. **Define stable units**: one unit per entry point + trust boundary (splitting distinct enforcement paths), keyed by symbol or route rather than line numbers, status, or a file × attack matrix.
1. **Track unit status**: record reviewed paths, checks, evidence, `finding_ids`, and status—`planned`, `covered` (examined with no open verification gap, even if findings exist), `blocked` (partial evidence + exact blocker), `deferred` (unchecked), or `excluded` (scope reason).
1. **Revalidate on change**: re-check callers, controls, and config before reusing prior records; keep blocked/deferred items visible and archive superseded evidence under its original commit.

## Challenge coverage separately

Audit the coverage map itself (ideally via a fresh reviewer when authorized, otherwise noting same-reviewer limits): check missed entry points, alternate/retry/background routes, lifecycle edges, and weak exclusions without inflating gaps into vulnerabilities. Reserve budget for verification and reporting; if time runs out, mark remaining units `deferred` and `run_status: "partial"`.

## Keep findings stable

Key each root cause by its enforcing control (merging multi-route hits on one defect, separating independent control failures):

- **Shared fields**: coverage units, actor, preconditions, boundary failure, input-to-operation trace, and supporting/contrary evidence.
- **Confirmed**: observed impact, severity, confidence, minimal fix, and regression plan.
- **Unresolved**: exact missing fact and safe next check (omit severity; do not report as a confirmed vuln).
- **Refuted**: disproving control or impossible precondition (retain to avoid re-triaging; one refutation does not close the unit).

Verify unique IDs, valid links, redacted examples, `coverage_review: "done"`, and `run_status` (`complete` only when all in-scope checks and verifications finish).

## Provenance and scope

Independently authored after reviewing [Cloudflare security-audit-skill at `c1c8a8c`](https://github.com/cloudflare/security-audit-skill/tree/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8) (2026-09-20; [MIT license](https://github.com/cloudflare/security-audit-skill/blob/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/LICENSE)); no upstream scripts, schemas, or prose are vendored.
