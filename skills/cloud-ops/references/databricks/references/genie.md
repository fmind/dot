# Genie Code CLI (`genie`)

`genie` uses `databricks` (>= 1.0.0) `~/.databrickscfg` profiles, Unity Catalog, Partner-powered AI, and Unity Gateway (`GENIE_CODE_CLI` in `system.billing.usage`). It loads repo `AGENTS.md`, `.agents/skills/`, `.genie/`, `~/.agents/skills/`, and `$GENIE_HOME/skills/` (default `~/.genie`; bundled skills in `.system/`).

```bash
genie doctor --json
genie exec --json --ephemeral -s read-only -C <dir> "PROMPT"
genie review --uncommitted
```

## Rules and Gotchas

- **Profile flag**: `genie -p <name>` layers `$GENIE_HOME/<name>.config.toml`, not `~/.databrickscfg` (pick the Databricks profile interactively or set `DATABRICKS_CONFIG_PROFILE`).
- **MCP secrets**: `--env KEY=VAL` writes literals to `config.toml`; register stdio (`genie mcp add <name> -- <cmd> <args...>`) and forward secrets via `env_vars = ["ENV_VAR"]` in `$GENIE_HOME/config.toml` or `with-secret`. Use `--url <url> --bearer-token-env-var ENV_VAR` for HTTP.
- **Sandboxing**: use `-s read-only` or `-s workspace-write` (never `-s danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`, or `--dangerously-bypass-hook-trust` on untrusted repos; `genie review` omits `-s`, and `genie exec --ignore-user-config --ignore-rules` isolates untrusted runs).
- **Layout & compliance**: `bin/genie` resolves `genie-package.json` for `genie-path/rg` and `genie-resources/` (keep the mise package intact); `--search` is unavailable on compliance-security-profile workspaces.

## Documentation

- [Genie Code CLI](https://docs.databricks.com/aws/en/genie-code/genie-code-cli) · [Releases](https://github.com/databricks/genie-code-cli/releases)
