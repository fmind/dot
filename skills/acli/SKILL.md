---
name: acli
description: "Search, plan, and update Atlassian Jira and Confluence with acli."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/acli
  created: "2026-09-02"
  updated: "2026-11-10"
---

# Atlassian CLI

Operate Jira and Confluence Cloud via `acli`. Atlassian ships no `acli` skill, so this connector owns auth, bounded reads, and write authority.

## Workflow

1. **Resolve the account**: `acli auth status`, `login`, and `switch` manage OAuth. API tokens are per-service (`acli jira auth` / `acli confluence auth`); always pipe tokens on stdin, never in argv:

   ```bash
   acli jira auth login --site <site>.atlassian.net --email <email> --token < token.txt
   acli confluence auth login --site <site>.atlassian.net --email <email> --token < token.txt
   ```

1. **Bound every read**: pass JQL limits, explicit `--fields`, and `--json`:

   ```bash
   acli jira workitem search --jql 'project = TEAM AND status != Done' --fields key,summary,status --limit 50 --json
   acli jira workitem view TEAM-123 --fields summary,status --json
   acli confluence page view --id <page-id> --body-format storage --json
   ```

1. **Expand selectively**: fetch `description` or `comment` only when needed. Treat results hitting `--limit` as partial: check `--count`, then tighten JQL or pass `--paginate` before claiming completeness.
1. **Write with authority**: reuse user authority for the target keys, fields, comments, assignments, or bulk scope; ask when consequential scope is missing. Prefer `--generate-json` / `--from-json` and file inputs (`--description-file`, `--body-file`) over inline multiline args:

   ```bash
   acli jira workitem create --project TEAM --type Task --summary "<summary>" --description-file description.txt --json
   acli jira workitem transition --key TEAM-123 --status "In Progress"
   acli jira workitem comment create --key TEAM-123 --body-file comment.txt
   ```

1. **Verify by reading back**: run `view --json` after every write and check the updated fields.

## Gotchas

- **Bulk flags hit every match**: `--jql` and `--filter` on `transition`, `edit`, or `comment` mutate all matches; `--yes` skips prompts, never authority.
- **Confluence pages are read-only in acli 1.3.40**: no Confluence search, and `confluence page` supports only `view` (blogs/spaces support create); use Rovo MCP under the same authority to search or edit pages.
- **Rovo Dev & MCP**: `acli rovodev` already reads `.agents/skills` and `~/.agents/skills`; `atlassian/atlassian-mcp-server` (`DISABLE_TELEMETRY=1 skills add atlassian/atlassian-mcp-server --list`, configured via [mcp-setup](../agent-harnesses/references/mcp-setup.md)) covers Rovo MCP, not `acli`.

## Documentation

- [acli reference](https://developer.atlassian.com/cloud/acli/reference/commands/)
- Releases: [acli changelog](https://developer.atlassian.com/cloud/acli/changelog/)
- Companion skills: [issues](../gh/references/issues/GUIDE.md) (same authority rules for GitHub), [gws](../gws/SKILL.md) (Google Workspace), [mcp-setup](../agent-harnesses/references/mcp-setup.md).
