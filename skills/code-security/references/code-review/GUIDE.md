---
name: code-review
description: "Assess code and repository security; verify findings and repairs."
---

# Code and Repository Security Review

Audit code and delivery controls in a `uv`-managed Python project, preserving intentional agent/admin autonomy (reviews never authorize config mutations).

## Workflow

1. **Trace and verify controls**: name asset, legitimate operation, and attacker capability; trace entry points, callers, config, and error/retry/cache paths rather than trusting names, types, or prompts; verify derived-path writes/deletes resolve strictly inside (never equal to) an allowlisted root with ownership proof beyond a marker file; enforce [ssrf-egress.md](references/ssrf-egress.md) at connect time on untrusted URLs/redirects; prove claims (`confirmed`, `refuted`, `unresolved`) via reproducer or isolated trace, fix shared boundaries with a failing-first regression test, and hunt variants via `rg` or `ast-grep`.
1. **Scan for leaks**: run working-tree and full-history scans per [betterleaks](../betterleaks.md), treating confirmed leaks as incidents (rotate only within authorized scope).
1. **Eliminate plaintext secrets**: inject runtime secrets via secret manager (Secret Manager on Cloud Run), scoped launchers, or encrypted stores; never shell out to `/usr/bin/security -w` on third-party macOS Keychain items (partition ACLs block it and pop modal prompts) — use the CLI's token subcommand, env tokens, or `0600` files.
1. **Audit locks and installed tools**: run `uv audit --preview-features audit-command --locked` plus `--script <file>` (`--locked` if `<file>.lock` exists) for PEP 723 scripts, triaging per [uv](../../../python-stack/references/foundation/GUIDE.md#uv); audit installed `npm:`/`pypi:` graphs in place via [installed-tools.md](references/installed-tools.md).
1. **Vet new packages**: check install hooks, model loaders, runtime downloads, and publisher provenance; enable `UV_MALWARE_CHECK=1` with `--preview-features malware-check` on dependency-mutating commands (`uv add`, install `uv sync --locked`, upgrades per [Python foundation](../../../python-stack/references/foundation/GUIDE.md#uv); queries `api.osv.dev` and fails closed offline).
1. **Scan IaC, deps, SAST, and licenses**: run `check:scan` per [trivy](../trivy/GUIDE.md) (and [sonarqube](../sonarqube.md) when SonarQube gates the repo), state enabled scanners, and fix or justify `HIGH`/`CRITICAL` findings.
1. **Audit workflows and Dependabot**: pass `check:actions` ([jactionlint](../../../github-actions/references/jactionlint.md): least privilege, SHA pins, no template injection, `persist-credentials: false`) and enable security-only [dependabot](../../../github-actions/references/dependabot.md) for `uv.lock` and Actions.
1. **Harden containers and cloud**: build non-root images ([containerize](../../../docker/references/containerize/GUIDE.md)), scan/SBOM/sign/attest digests ([cosign](../../../docker/references/cosign.md)), and enforce private services, split deployer/runtime SAs, and keyless CI ([cloud-run](../../../cloud-run/SKILL.md), [infra-as-code](../../../infra-as-code/SKILL.md)).
1. **Model threats and red-team AI**: apply [threat-model](../threat-model.md) on auth, PII, agent tools, or public surfaces, and [ai-red-team](../ai-red-team/GUIDE.md) on retrieval, model outputs, and tool authority.

## Gate & Report

- `mise run check` runs `check:leaks` plus configured `check:vuln`, `check:scan`, and `check:actions`; scheduled `security.yml` ([github-actions](../../../github-actions/references/ci-cd/GUIDE.md)) runs full-history leak and `check:network` audits, and CD scans built images before promotion.
- **Bound every claim**: report exact revision, `path:line`, actor/preconditions, input-to-operation trace, reproduction, lockfile/digest/workflow scope, and minimal fix ([full-review](../../../full-review/SKILL.md) owns severity; missing tools/DBs/locks are coverage gaps, and suppressions are not fixes).

## Documentation

- Method ideas adapted from [Trail of Bits skills at `2be6433`](https://github.com/trailofbits/skills/tree/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a) (CC-BY-SA-4.0; no text copied) · [OpenSSF Scorecard](https://securityscorecards.dev) · Companion: [skill-security-review](../skill-security-review/GUIDE.md).
