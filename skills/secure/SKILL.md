---
name: secure
description: "Run the Python repository security pass across secrets, dependencies, IaC, workflows, images, provenance, and threat boundaries. Use for a security review."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/secure
  created: "2026-07-04"
  updated: "2026-09-06"
---

# Secure a Python Repository

Run one ordered gate for a uv-managed Python project. The linked tool skills own command details; this skill owns coverage, order, and honest reporting.

## Workflow

1. **Leaks**: run the full-history scan and wire the staged hook per [gitleaks](../gitleaks/SKILL.md). Treat a finding as compromised and rotate it before continuing.
1. **Secrets at rest**: move plaintext credentials to environment variables or encrypted `*.enc.*` files per [sops-secrets](../sops-secrets/SKILL.md). Cloud Run receives runtime values from Secret Manager.
1. **Dependency graphs**: run `uv audit --preview-features audit-command --locked` against `uv.lock` without the experimental-command warning. Audit exact installed `npm:` and `pipx:` tool graphs separately with [installed-tools.md](references/installed-tools.md); do not substitute a newly resolved graph for installed evidence.
1. **Repository and IaC**: run `check:scan` per [trivy](../trivy/SKILL.md) for vulnerabilities, misconfiguration, secrets, and licenses. Fix or justify every `HIGH` or `CRITICAL` finding.
1. **Workflows**: run `check:actions` per [zizmor](../zizmor/SKILL.md). Keep permissions least privilege, avoid template injection, pin actions, and set `persist-credentials: false`.
1. **Updates**: configure [dependabot](../dependabot/SKILL.md) for the Python lock and GitHub Actions so the same gates inspect upgrades.
1. **Images and provenance**: build the pinned non-root image per [containerize](../containerize/SKILL.md). Scan the exact digest, generate an SBOM, then sign, verify, and attest it per [cosign](../cosign/SKILL.md).
1. **Runtime and infrastructure**: keep services private, use separate deployer and runtime identities, and use keyless CI per [cloud-run](../cloud-run/SKILL.md). Review declarative infrastructure with [terraform](../terraform/SKILL.md).
1. **Threat boundaries**: run [threat-model](../threat-model/SKILL.md) for authentication, personal data, tool-using agents, or public exposure; scanners cannot establish design safety.

## Gate

`mise run check` owns the checks shared by hooks and CI (advisory databases may require network access): `check:leaks`, `check:vuln`, `check:scan`, and `check:actions`. Keep full-history and published-image scans in the scheduled `security.yml` per [github-actions](../github-actions/SKILL.md).

## Report

- List findings by severity, affected revision or digest, and the applied fix or narrow justified ignore.
- State the proof boundary for every command: working tree, history range, lockfile, image digest, IaC tree, workflow set, signature identity, and issuer.
- Report missing tools, databases, lockfiles, inaccessible registries, malformed output, and skipped targets as coverage gaps.
- Never describe a suppression as a fix or one scanner as proof for another control.

## Documentation

- [OpenSSF Scorecard](https://securityscorecards.dev)
- Companion skills: [skill-security-review](../skill-security-review/SKILL.md) for third-party skills and [incident-response](../incident-response/SKILL.md) when an incident is active.
