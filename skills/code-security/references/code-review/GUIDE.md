---
name: code-review
description: "Assess code and repository security; verify findings and repairs."
---

# Code and Repository Security Review

Audit code and delivery controls in a uv-managed Python project. Start at [trace-and-verify.md](references/trace-and-verify.md) for a focused change/finding, or run the full pass below (preserving intentional autonomy; reviews never authorize config mutations).

## Workflow

Track broad or repeated audits with [audit-coverage.md](references/audit-coverage.md) and optional [audit-record.json](templates/audit-record.json).

1. **Trace code and controls** per [trace-and-verify.md](references/trace-and-verify.md) across callers, config, and variants.
1. **Scan for leaks**: run working-tree and full-history scans per [betterleaks](../betterleaks.md), treating confirmed leaks as incidents (rotate only within authorized scope).
1. **Eliminate plaintext secrets**: inject runtime secrets via secret manager (Secret Manager on Cloud Run), scoped launchers, or encrypted stores; never shell out to `/usr/bin/security -w` on third-party macOS Keychain items (partition ACLs block it and pop modal prompts)—use the CLI's token subcommand, env tokens, or `0600` files.
1. **Audit locks and installed tools**: run `uv audit --preview-features audit-command --locked` plus `--script <file>` (`--locked` if `<file>.lock` exists) for PEP 723 scripts, triaging per [uv audit](../../../python-stack/references/uv.md#gotchas); audit installed `npm:`/`pypi:` graphs in place via [installed-tools.md](references/installed-tools.md).
1. **Vet new packages**: check install hooks, model loaders, runtime downloads, and publisher provenance; enable `UV_MALWARE_CHECK=1` with `--preview-features malware-check` on dependency-mutating commands (`uv add`, install `uv sync --locked`, upgrades per [Python foundation](../../../python-stack/references/foundation/GUIDE.md) and [uv](../../../python-stack/references/uv.md#workflow); queries `api.osv.dev` and fails closed offline).
1. **Scan IaC, deps, and licenses**: run `check:scan` per [trivy](../trivy/GUIDE.md), state enabled scanners, and fix or justify `HIGH`/`CRITICAL` findings.
1. **Audit workflows and Dependabot**: pass `check:actions` ([jactionlint](../../../github-actions/references/jactionlint.md): least privilege, SHA pins, no template injection, `persist-credentials: false`) and enable security-only [dependabot](../../../github-actions/references/dependabot.md) for `uv.lock` and Actions.
1. **Harden containers and cloud**: build non-root images ([containerize](../../../docker/references/containerize/GUIDE.md)), scan/SBOM/sign/attest digests ([cosign](../../../docker/references/cosign.md)), and enforce private services, split deployer/runtime SAs, and keyless CI ([cloud-run](../../../cloud-run/SKILL.md), [infra-as-code](../../../infra-as-code/SKILL.md)).
1. **Model threats and red-team AI**: apply [threat-model](../threat-model.md) on auth, PII, agent tools, or public surfaces, and [ai-red-team](../ai-red-team/GUIDE.md) on retrieval, model outputs, and tool authority.

## Gate

`mise run check` runs `check:leaks` plus configured `check:vuln`, `check:scan`, and `check:actions` tasks; scheduled `security.yml` ([github-actions](../../../github-actions/references/ci-cd/GUIDE.md)) runs full-history leak and `check:network` audits, and CD workflows scan built images before promotion.

## Report

- **Bound every claim**: name exact tree, commit range, lockfile, digest, IaC/workflow scope, and signer/issuer; missing tools, DBs, locks, or registries are coverage gaps, and suppressions are not fixes.

## Documentation

- Method ideas adapted from [Trail of Bits skills at `2be6433`](https://github.com/trailofbits/skills/tree/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a) (CC-BY-SA-4.0; no text copied) · [OpenSSF Scorecard](https://securityscorecards.dev)
- Companion skill: [skill-security-review](../skill-security-review/GUIDE.md).
