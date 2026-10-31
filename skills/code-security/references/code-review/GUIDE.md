---
name: code-review
description: "Assess code and repository security; verify findings and repairs."
---

# Code and Repository Security Review

Review security-sensitive code and the delivery chain of a uv-managed Python project. For implementation or a specific finding, start with [code review](references/trace-and-verify.md); for a repository audit, use the workflow below. The linked tool skills own scanner commands. Reuse the task's authorization and preserve deliberate autonomy settings; a review does not authorize configuration changes.

## Workflow

For a broad or repeated audit, use [coverage and finding records](references/audit-coverage.md) and, when persistent artifacts are useful, the optional [audit record](templates/audit-record.json). A focused finding review does not need a ledger.

1. **Review code and controls**: trace attacker-controlled inputs to security decisions with [code review](references/trace-and-verify.md). Check the actual callers and effective configuration; validate suspected findings and search for related defects before reporting coverage.
1. **Scan for leaks**: run the working-tree gate and the full-history scan per [gitleaks](../gitleaks.md). Treat a confirmed credential exposure as an incident; prepare rotation and perform it only within the established credential and service authority.
1. **Remove plaintext secrets at rest**: move plaintext credentials to environment variables injected by a secret manager or scoped launcher, or to the encrypted store the project already uses. Never shell out to `/usr/bin/security -w` to read third-party CLI macOS Keychain items (whose partition ACLs block `/usr/bin/security` and trigger modal prompts in background watchers); use the CLI's own token subcommand, environment tokens, or a `0600` file-backed store. Cloud Run receives runtime values from Secret Manager.
1. **Audit dependency graphs**: run `uv audit --preview-features audit-command --locked` against `uv.lock` without the experimental-command warning, plus `--script <file>` (with `--locked` only when `<file>.lock` exists) for each PEP 723 script, which the project audit skips. Record accepted advisories with a reason comment under `[tool.uv.audit]` in `pyproject.toml`: `ignore-until-fixed` for an advisory without a fix, which resurfaces once one ships, and `ignore` only for an advisory shown not to apply or a fixed one you cannot take yet (name the blocker). Audit exact installed `npm:` and `pipx:` tool graphs separately with [installed-tools.md](references/installed-tools.md); do not substitute a newly resolved graph for installed evidence.
1. **Vet new dependency behavior**: inspect newly introduced dependencies for install hooks, executable model loading, runtime downloads, and sensitive data access. Verify upstream and publisher evidence separately from advisory results; unavailable ownership data is a coverage gap, not evidence of compromise. For uv projects, recommend the preview malware check on dependency-changing commands only (`UV_MALWARE_CHECK=1` with `--preview-features malware-check` on `uv add`, the install task's `uv sync --locked`, and upgrades, as the [Python foundation](../../../python-stack/references/foundation/GUIDE.md) tasks do): it stops when a locked package matches an OSV malicious-package advisory, sends locked package names and versions to `api.osv.dev`, fails closed offline, and runs after resolution, so it cannot stop code an sdist build already ran. Enabling it for every `uv run` adds about a second per call.
1. **Scan repository and IaC**: run `check:scan` per [trivy](../trivy/GUIDE.md); report which vulnerability, misconfiguration, secret, and license scanners the effective policy enables. Fix or justify every `HIGH` or `CRITICAL` finding.
1. **Audit workflows**: run `check:actions` per [zizmor](../../../github-actions/references/zizmor.md). Keep permissions least privilege, avoid template injection, pin actions, and set `persist-credentials: false`.
1. **Automate security fixes**: enable Dependabot alerts and security updates and add the security-only config from [dependabot](../../../github-actions/references/dependabot.md) for the Python lock and GitHub Actions, so the same gates inspect every fix PR.
1. **Scan, sign, and attest images**: when the project ships a container, build the pinned non-root image per [containerize](../../../docker/references/containerize/GUIDE.md). Scan the exact digest, generate an SBOM, then sign, verify, and attest it per [cosign](../../../docker/references/cosign.md) within the authorized delivery scope.
1. **Harden runtime and infrastructure**: keep services private, use separate deployer and runtime identities, and use keyless CI per [cloud-run](../../../cloud-run/SKILL.md). Review declarative infrastructure with [infra-as-code](../../../infra-as-code/SKILL.md).
1. **Threat-model sensitive boundaries**: run [threat-model](../threat-model.md) for authentication, personal data, tool-using agents, or public exposure; scanners cannot establish design safety.
1. **Test AI systems adversarially**: use [ai-red-team](../../../ai-red-team/SKILL.md) for adversarial tests of retrieval, model output, tool authority, and resulting state. PyRIT complements dependency and code checks; it does not replace them.

## Gate

`mise run check` owns the checks shared by hooks and CI (advisory databases may require network access): `check:leaks`, `check:vuln`, `check:scan`, and `check:actions`. Keep full-history and published-image scans in the scheduled `security.yml` per [github-actions](../../../github-actions/references/ci-cd/GUIDE.md).

## Report

- **List findings with their evidence**: by severity, affected revision or digest, and the applied fix or narrow justified ignore.
- **State each command's proof boundary**: working tree, history range, lockfile, image digest, IaC tree, workflow set, signature identity, and issuer.
- **Treat missing inputs as coverage gaps**: report missing tools, databases, lockfiles, inaccessible registries, malformed output, and skipped targets as coverage gaps.
- **Never overstate scan results**: a successful scan does not mean zero residual risk. Never describe a suppression as a fix or one scanner as proof for another control.

## Documentation

- [Trail of Bits review and incorporation decisions](references/trailofbits-review.md)
- [OpenSSF Scorecard](https://securityscorecards.dev)
- Companion skills: [skill-security-review](../skill-security-review/GUIDE.md) for third-party skills and [incident-response](../../../production-readiness/references/incident-response.md) when an incident is active.
