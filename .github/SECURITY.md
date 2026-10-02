# Security Policy

## Supported versions

Only the [latest release](https://github.com/fmind/dot/releases/latest) is supported. Fixes land on `main` and ship in the next release; older tags receive no backports.

## Reporting a vulnerability

Report privately through [GitHub private vulnerability reporting](https://github.com/fmind/dot/security/advisories/new) or to [contact@fmind.dev](mailto:contact@fmind.dev), the contact address published on [fmind.dev](https://www.fmind.dev/). Include the affected version, impact, and a minimal reproduction with sensitive data removed. Do not open a public issue for an undisclosed vulnerability, and never include secrets or tokens in a report.

This is a personal project maintained on a best-effort basis; there is no response-time commitment.

## Scope

In scope: `install.sh`, the chezmoi source tree, the `dot` CLI, the GitHub workflows, and the agent configurations and skills shipped here.

By design, setup runs third-party installers (mise.run, then the Grok and Antigravity vendor scripts during apply), fetches theme files from `fmind/theme` `main` without a checksum, and installs tools with signature and provenance verification off; see [`install.sh`](../install.sh) and the trade-off stated in [`dot_config/mise/config.toml.tmpl`](../dot_config/mise/config.toml.tmpl). Report vulnerabilities in mise, chezmoi, the agent harnesses, or any installed tool to their upstream projects.
