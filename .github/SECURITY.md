# Security Policy

## Supported versions

Only the [latest release](https://github.com/fmind/dot/releases/latest) is supported. Fixes land on main and ship in the next release; older tags receive no backports.

## Reporting a vulnerability

Report privately through [GitHub private vulnerability reporting](https://github.com/fmind/dot/security/advisories/new) or to [contact@fmind.dev](mailto:contact@fmind.dev), the contact address published on [fmind.dev](https://www.fmind.dev/). Include the affected version, impact, and a minimal reproduction with sensitive data removed. Do not open a public issue for an undisclosed vulnerability, and never include secrets or tokens in a report.

This is a personal project maintained on a best-effort basis; there is no response-time commitment.

## Scope

In scope: [`install.sh`](../install.sh), the chezmoi source tree, the `dot` CLI, the GitHub workflows, SHA-256 checksum/pin integrity for externals, and the agent configurations and skills shipped here (see [installation & trust boundaries](../README.md#installation), [folder trust](../skills/dot-cli/references/daily-workflows.md#folder-trust), and [mise settings](../dot_config/mise/config.toml)).

Accepted workstation trade-offs (known behavior, not vulnerabilities):

- **Workstation vs repository verification:** repository tools ([`mise.toml`](../mise.toml)) keep mise's default signature and provenance verification enabled for CI. Global workstation tools ([`dot_config/mise/config.toml`](../dot_config/mise/config.toml)) disable optional cosign/minisign/SLSA/GitHub attestation checks while keeping npm provenance, packslip signatures, and SHA-256 download digests active, and enable background `mise` self-updates every 24h (`self_update.auto = "24h"`).
- **Autonomous single-user agents:** shipped Antigravity and Copilot settings intentionally grant autonomous permissions on trusted local workspaces (Antigravity adds credential-store path denies; Copilot runs unrestricted without path denies). Keep untrusted repositories outside trusted paths or inside isolated containers/VMs.

Out of scope:

- **Third-party installers:** initial setup invokes external installer scripts (`mise.run` and the Antigravity vendor installer) before locked verification applies.
- **Upstream vulnerabilities:** report flaws in upstream tools, theme/font repositories, mise, chezmoi, or agent harnesses directly to their upstream maintainers (pin or checksum bypasses in this repository remain in scope).
