---
name: aws
description: "Operate AWS accounts and SSO profiles with the aws CLI."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/aws
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Amazon Web Services CLI

Operate AWS accounts, IAM, S3, ECS, and CloudWatch with `aws`.

## Workflow

1. **Verify profile and caller identity**: never assume roles or run under ambiguous profiles:

   ```bash
   aws sts get-caller-identity --profile <profile> --output json --no-cli-pager
   aws configure list-profiles
   ```

1. **Sign in cleanly**: prefer IAM Identity Center (`aws sso login --profile <profile>`), else `aws login --profile <profile>` (`--remote` on headless hosts) over static keys.
1. **Pin `--profile` and `--region`** on every consequential call so env vars cannot redirect targets.
1. **Bound reads first**: combine server-side filters, `--max-items`, and `--query` (JMESPath) before mutating state:

   ```bash
   aws ecs list-clusters --profile <profile> --region <region> --max-items 20 --output json --no-cli-pager
   ```

1. **Authorize mutations**: resource creation, security groups, IAM policies, and deletions require user approval.

## Gotchas

- **`--query` filters client-side**: pair with `--max-items` (`--page-size` only sizes HTTP pages), keep `NextToken` in projections, and flag capped output as partial. Pass `--no-cli-pager --cli-error-format json` for structured `Code`/`Message` diagnostics without credential-leaking `--debug`.
- **Failures are findings**: report `AccessDeniedException` or missing roles directly instead of escalating IAM permissions.

## Official Skills

Upstream: [AWS Agent Toolkit](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/). Inspect read-only via `aws agent-toolkit list-available-skills` / `search-skills --search-query <topic>`, `get-skill-metadata --skill-name <name>`, and `get-skill-file --skill-name <name> --file-path SKILL.md --skill-version <version>`, installing only under [vendor-skill policy](../agent-project/references/vendor-skills.md). Never run `aws configure agent-toolkit --yes` (bulk-installs skills and MCP across hosts; `AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED=true` suppresses hints).

## Documentation

- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/) · [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/)
- Releases: [AWS CLI GitHub Releases](https://github.com/aws/aws-cli/releases)
- Companion skills: [infra-as-code](../infra-as-code/SKILL.md) (provisioned infrastructure), [code-security](../code-security/SKILL.md) (IAM audits).
