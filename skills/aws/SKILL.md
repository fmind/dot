---
name: aws
description: "Operate AWS accounts, resources, and SSO profiles with aws and aws-sso-util."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/aws
  created: "2026-09-16"
  updated: "2026-09-19"
---

# Amazon Web Services CLI

Use `aws` and `aws-sso-util` for AWS account, IAM, S3, ECS, and CloudWatch operations. [infra-as-code](../infra-as-code/SKILL.md) owns provisioned infrastructure, and [incident-response](../incident-response/SKILL.md) owns a live outage.

## Workflow

1. **Resolve identity and profile context**: inspect the active AWS profile, SSO session, and caller identity; never assume role or run commands under ambiguous profiles.

   ```bash
   aws sts get-caller-identity --profile <profile> --output json
   aws configure list-profiles
   ```

1. **Authenticate via SSO**: when credentials expire, refresh the session using AWS IAM Identity Center (SSO); avoid long-lived access keys.

   ```bash
   aws sso login --profile <profile>
   # Or using aws-sso-util:
   aws-sso-util login --profile <profile>
   ```

1. **Pin every consequential call**: pass `--profile <name>` and `--region <region>` explicitly so environment variables or shell defaults cannot redirect operations to the wrong account or region.
1. **Start read-only with bounded queries**: use `--query` (JMESPath) and `--max-items` to constrain results; describe resources, IAM policies, and CloudWatch metrics before changing anything.

   ```bash
   aws s3 ls --profile <profile>
   aws ecs list-clusters --profile <profile> --region <region> --max-items 20 --output json
   ```

1. **Plan mutations and confirm**: state the target ARN, expected before and after states, and rollback steps; resource creation, security group changes, policy updates, and deletions require user authorization; reuse existing authority rather than asking again.
1. **Apply and verify**: execute the mutation, then re-read the resource status to confirm the state change.

## Gotchas

- **Expired SSO tokens**: SSO tokens expire after their configured duration; refresh via `aws sso login` rather than falling back to static API keys.
- **`--query` client-side evaluation**: JMESPath queries in `--query` run client-side after downloading the page; for large resources, pair with `--max-items`; `--page-size` only changes each request size to prevent timeout.
- **Failures are findings**: report authorization (`AccessDeniedException`) or missing role errors directly; do not attempt permission escalation or modify IAM policies without authorization.

## Documentation

- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/) · [AWS CLI Command Reference](https://awscli.amazonaws.com/v2/documentation/api/latest/index.html)
- Releases: [AWS CLI GitHub Releases](https://github.com/aws/aws-cli/releases)
- Companion skills: [infra-as-code](../infra-as-code/SKILL.md) (provisioning), [security-review](../security-review/SKILL.md) (IAM audits), [incident-response](../incident-response/SKILL.md) (outages).
