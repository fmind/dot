---
name: aws
description: "Operate AWS accounts, SSO, IAM, S3, and ECS via aws."
---

# Amazon Web Services CLI

Operate AWS accounts, IAM, S3, ECS, and CloudWatch with `aws` (not globally installed in `fmind/dot`; pin per project via `mise use --pin awscli` or verify `command -v aws`).

## Workflow

1. **Verify profile and identity**: never assume roles or run under ambiguous profiles:
   ```bash
   aws sts get-caller-identity --profile <profile> --output json --no-cli-pager
   aws configure list-profiles
   ```
1. **Sign in**: prefer IAM Identity Center (`aws sso login --profile <profile>`), else `aws login --profile <profile>` (`--remote` headless) over static keys.
1. **Pin `--profile` and `--region`** on every call so env vars cannot redirect targets.
1. **Bound reads**: pair server filters, `--max-items`, and `--query` (JMESPath) before mutating:
   ```bash
   aws ecs list-clusters --profile <profile> --region <region> --max-items 20 --output json --no-cli-pager
   ```
1. **Authorize mutations**: resource creation, security groups, IAM, and deletions need approval.

## Gotchas

- **`--query` filters client-side**: pair with `--max-items` (`--page-size` sets HTTP pages), keep `NextToken`, and flag capped results partial. Pass `--no-cli-pager --cli-error-format json` for `Code`/`Message` errors without `--debug`.
- **Failures are findings**: report `AccessDeniedException` or missing roles instead of escalating IAM.

## Official Skills

Upstream: [AWS Agent Toolkit](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/). Inspect via `aws agent-toolkit list-available-skills|search-skills|get-skill-metadata|get-skill-file` and install only under [vendor-skill policy](../../agent-harnesses/references/vendor-skills.md). Never run `aws configure agent-toolkit --yes` (`AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED=true`).

## Documentation

- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/) · [Command Reference](https://docs.aws.amazon.com/cli/latest/) · [Releases](https://github.com/aws/aws-cli/releases)
- Companions: [infra-as-code](../../infra-as-code/SKILL.md) (provisioned infrastructure), [code-security](../../code-security/SKILL.md) (IAM audits).
