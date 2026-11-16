# Security Policy

## Supported versions

Only the [latest release](https://github.com/fmind/dot/releases/latest) is supported. Fixes land on main and ship in the next release; older tags receive no backports.

## Reporting a vulnerability

Report privately through [GitHub private vulnerability reporting](https://github.com/fmind/dot/security/advisories/new) or to [contact@fmind.dev](mailto:contact@fmind.dev), the contact address published on [fmind.dev](https://www.fmind.dev/). Include the affected version, impact, and a minimal reproduction with sensitive data removed. Do not open a public issue for an undisclosed vulnerability, and never include secrets or tokens in a report.

This is a personal project maintained on a best-effort basis; there is no response-time commitment.

## Scope

In scope: `install.sh`, the chezmoi source tree, the `dot` CLI, the GitHub workflows, and the agent configurations and skills shipped here ([trust model](../install.sh), [mise trade-offs](../dot_config/mise/config.toml)).

Out of scope and upstream boundaries:

- **Third-party installers**: setup invokes external installer scripts (`mise.run` and the Antigravity vendor installer during apply) before locked verification applies.
- **Workstation vs repository tool verification**: workstation tools skip aqua/GitHub signature and attestation checks while keeping npm provenance and packslip signatures active; repository tools keep mise defaults.
- **Theme and font pins**: theme files pin to an immutable upstream commit and fonts pin to release versions, both verified via SHA-256 checksums.
- **Upstream vulnerabilities**: report vulnerabilities in mise, chezmoi, agent harnesses, or installed tools directly to their upstream projects.
