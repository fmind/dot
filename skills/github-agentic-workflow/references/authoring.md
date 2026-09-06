# Copilot Agentic Workflow Authoring

1. **Choose the right job**: Use agentic workflows for context-dependent triage, investigation, review, reporting, documentation, or reviewable code changes. Use ordinary Actions when fixed inputs should produce predictable steps and outputs.
   - **Triggers**: Run manually, on a schedule, from GitHub events, or through guarded slash commands.
   - **Context and tools**: Read repository files, issues, pull requests, and Actions; opt into editing, allowlisted shell commands, web fetch, or trusted MCP servers.
   - **Safe outputs**: Request bounded issues, comments, labels, reviews, or pull requests for separate permission-scoped jobs to validate and apply.
1. **Install and diagnose**: Require GitHub Actions, repository write access, an authenticated `gh` CLI, and Copilot access. Install the extension once, then use `gh extension upgrade github/gh-aw` on later visits.
   ```bash
   gh auth status
   gh extension install github/gh-aw
   gh aw version
   gh aw doctor
   ```
1. **Initialize Copilot authoring**: Run `gh aw init --engine copilot`, then review its `.gitattributes`, `.github/skills/`, `.github/agents/`, `.github/mcp.json`, and Copilot setup workflow changes. This gives Copilot the official skill, custom agent, and MCP tools for creating and debugging workflows.
   ```bash
   gh aw init --engine copilot
   git diff -- .gitattributes .github/
   ```
1. **Choose one runtime identity within authorized GitHub scope**: Prefer organization-billed inference by declaring `copilot-requests: write`. Otherwise create a fine-grained PAT with the Copilot Requests account permission, store it as the `COPILOT_GITHUB_TOKEN` repository secret, and never expose it to the prompt or agent tools.
   ```bash
   gh secret set COPILOT_GITHUB_TOKEN
   ```
1. **Create the Markdown source**: Start with `gh aw new <workflow-name> --engine copilot`, or ask the initialized Copilot agent `agentic-workflows create ...`. Define the trigger, read permissions, tools, network, budgets, safe outputs, and precise instructions; adapt the [bounded Copilot starter](references/copilot-starter.md).
   ```bash
   gh aw new <workflow-name> --engine copilot
   ```
1. **Constrain capabilities**: Grant only required reads; restrict GitHub tools to the current repository and relevant toolsets; allowlist individual shell commands and network domains; prefer safe outputs over direct writes; set `staged: true`, `max-turns`, and both agent and threat-detection AI-credit caps for the first runs.
1. **Validate and compile**: Strict validation runs the compiler linters without emitting files; compilation produces `.github/workflows/<workflow-name>.lock.yml`. Review and eventually commit the human-authored `.md` and generated `.lock.yml` together.
   ```bash
   gh aw validate --strict
   gh aw compile
   git diff -- .github/workflows/
   ```
1. **Pilot deliberately**: First preview dispatch with `--dry-run`; with explicit approval for Actions and Copilot spend, run the committed workflow while safe outputs remain staged. Review the Actions summary, then disable staged mode only after outputs are consistently correct.
   ```bash
   gh aw run <workflow-name> --dry-run
   gh aw run <workflow-name>
   gh aw status --ref main
   gh aw logs <workflow-name>
   ```
1. **Audit and maintain**: Use `gh aw audit <run-id>` for prompts, tool calls, network activity, tokens, and AI Credits. Upgrade intentionally, review migrations and generated diffs, then repeat strict validation and compilation.
   ```bash
   gh aw audit <run-id>
   gh aw upgrade
   ```
