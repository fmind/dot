---
name: aws
description: "Operate AWS accounts and SSO profiles with aws and aws-sso-util."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/aws
  created: "2026-09-16"
  updated: "2026-10-07"
---

# Amazon Web Services CLI

Use `aws` and `aws-sso-util` for AWS account, IAM, S3, ECS, and CloudWatch operations.

## Workflow

1. **Resolve identity and profile context**: inspect the active AWS profile, SSO session, and caller identity; never assume role or run commands under ambiguous profiles.

   ```bash
   aws sts get-caller-identity --profile <profile> --output json --no-cli-pager
   aws configure list-profiles
   ```

1. **Authenticate via SSO**: when credentials expire, refresh the session using AWS IAM Identity Center (SSO); avoid long-lived access keys. When Identity Center is unavailable, `aws login` exchanges a console sign-in for short-lived credentials; add `--remote` on a host without a local browser.

   ```bash
   aws sso login --profile <profile>
   # Or using aws-sso-util:
   aws-sso-util login --profile <profile>
   # Without Identity Center:
   aws login --profile <profile>
   ```

1. **Pin every consequential call**: pass `--profile <name>` and `--region <region>` explicitly so environment variables or shell defaults cannot redirect operations to the wrong account or region.
1. **Start read-only with bounded queries**: use `--query` (JMESPath) and `--max-items` to constrain results; describe resources, IAM policies, and CloudWatch metrics before changing anything.

   ```bash
   aws s3 ls --profile <profile>
   aws ecs list-clusters --profile <profile> --region <region> --max-items 20 --output json --no-cli-pager
   ```

1. **Authorize mutations**: resource creation, security group changes, policy updates, and deletions require user authorization; reuse existing authority rather than asking again.

## Gotchas

- **Refresh expired SSO tokens**: SSO tokens expire after their configured duration; refresh via `aws sso login` rather than falling back to static API keys.
- **`--query` runs client-side**: select needed fields and pair with supported server-side filters and `--max-items`; `--page-size` only changes request size, not total results. Preserve `NextToken` in projections, report capped results as partial, and resume deliberately when completeness is required. Use `--no-cli-pager` for agent calls; avoid debug output around credentials.
- **Failures are findings**: report authorization (`AccessDeniedException`) or missing role errors directly; do not attempt permission escalation or modify IAM policies without authorization.

## Official Skills

AWS publishes agent skills through the [Agent Toolkit](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/). Review candidates read-only with `aws agent-toolkit list-available-skills` or `search-skills --search-query <topic>`, `get-skill-metadata --skill-name <name>` (version and file list), and `aws agent-toolkit get-skill-file --skill-name <name> --file-path SKILL.md --skill-version <version>`, then install only through the shared [vendor-skill policy](../agent-project/references/vendor-skills.md). Never run `aws configure agent-toolkit --yes`: it installs default skills into every detected agent and configures the AWS MCP server. The workstation sets `AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED=true` to suppress the toolkit prompt.

## Documentation

- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/) · [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/)
- Releases: [AWS CLI GitHub Releases](https://github.com/aws/aws-cli/releases)
- Companion skills: [infra-as-code](../infra-as-code/SKILL.md) (provisioned infrastructure), [code-security](../code-security/SKILL.md) (IAM audits), [incident-response](../incident-response/SKILL.md) (live outages).
