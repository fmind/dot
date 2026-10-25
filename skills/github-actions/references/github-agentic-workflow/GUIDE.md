---
name: github-agentic-workflow
description: "Design, compile, test, and audit GitHub Agentic Workflows."
---

# GitHub Agentic Workflow

Run Copilot in GitHub Actions for bounded investigation, triage, review, and documentation. Keep deterministic builds/tests/deployment in [github-actions](../ci-cd/GUIDE.md).

## Workflow

1. **Choose the job**: use reasoning only where context changes the work; use ordinary Actions when fixed inputs should produce predictable steps and outputs. Resolve repository, candidate git revision, expected output, and existing authority.
1. **Install and diagnose**: require GitHub Actions, repository write access, an authenticated `gh` CLI, and Copilot access, then read the repository's generated dispatcher when present. Install the extension once; run `gh extension upgrade github/gh-aw` only when an upgrade is in scope, then review generated changes and revalidate.

   ```bash
   gh auth status
   gh extension install github/gh-aw
   gh aw version
   gh aw doctor
   ```

1. **Initialize Copilot authoring**: run `gh aw init --engine copilot`, then review its `.gitattributes`, `.github/skills/`, `.github/agents/`, `.github/mcp.json`, and Copilot setup workflow changes with `git diff -- .gitattributes .github/`.
1. **Choose one runtime identity** within authorized GitHub scope, per the [starter's authentication paths](references/copilot-starter.md#authentication): prefer organization-billed inference with `copilot-requests: write`; otherwise store a fine-grained PAT with the Copilot Requests account permission through `gh secret set COPILOT_GITHUB_TOKEN`, and never expose it to the prompt or agent tools.
1. **Create the Markdown source**: run `gh aw new <workflow-name> --engine copilot` or ask the initialized Copilot agent `agentic-workflows create ...`; define the trigger, read permissions, tools, network, budgets, safe outputs, and precise instructions, adapting the [bounded Copilot starter](references/copilot-starter.md).
1. **Constrain capabilities**: grant only required reads; restrict GitHub tools to the current repository and relevant toolsets; allowlist individual shell commands and network domains; prefer safe outputs over direct writes; set `staged: true`, `max-turns`, and both agent and threat-detection AI-credit caps for the first runs.
1. **Validate and compile locally**: `gh aw validate --strict` runs the compiler linters without emitting files; `gh aw compile` writes `.github/workflows/<workflow-name>.lock.yml`. Review both with `git diff -- .github/workflows/` and commit the `.md` source and generated `.lock.yml` together.
1. **Pilot when authorized**: preview with `gh aw run <workflow-name> --dry-run`; with explicit approval for Actions and Copilot spend, `gh aw run <workflow-name>` the committed workflow while safe outputs stay staged, then inspect `gh aw status --ref main`, `gh aw logs <workflow-name>`, and the Actions summary. Remove staging only after outputs are consistently correct, then recompile, review the lock diff, and authorize another run.
1. **Audit and maintain**: `gh aw audit <run-id>` shows prompts, tool calls, network activity, tokens, and AI Credits. Run `gh aw upgrade` intentionally, review migrations and generated diffs, then repeat strict validation and compilation.

## Gotchas

- **Copilot plays two roles**: `gh aw init --engine copilot` configures Copilot as the authoring assistant; `engine: copilot` plus runtime authentication selects it inside the Actions workflow.
- **Recompile after frontmatter edits**: Markdown body edits load at runtime, but frontmatter edits require recompilation; repository policy may still require compiling every change.
- **Give Copilot web search through MCP**: `gh aw compile` rejects `tools.web-search` for Copilot ([web search](https://github.github.com/gh-aw/reference/web-search/)); it is native only for Claude and Codex ([engine reference](https://github.github.com/gh-aw/reference/engines/)). Confirm the installed compiler supports it and validate the workflow before use; add an external MCP search service only when the native capability does not meet the task.
- **Writes and spend need explicit authority**: `gh aw run`, safe outputs without staged mode, `--push`, and `--auto-merge-prs` can mutate GitHub or consume paid resources; require explicit authority for the exact repository and action.
- **Imported workflows are supply-chain input**: Treat their triggers, permissions, tools, network, instructions, safe outputs, and lock files as executable supply-chain input; prefer pinned trusted releases.
- **Guardrails are boundaries, not proof**: Sandboxing, integrity filtering, threat detection, and safe outputs reduce blast radius; they do not make broad permissions or unreviewed output safe.

## Official Skills

- `gh aw init --engine copilot` installs GitHub's repository-scoped `agentic-workflows` dispatcher skill, Copilot custom agent, and MCP wiring. Use those generated, upgradeable assets for detailed authoring instead of copying the evolving upstream schema into this global skill.

## Documentation

- [Overview](https://github.github.com/gh-aw/introduction/overview/) · [Copilot engine](https://github.github.com/gh-aw/engines/copilot/) · [CLI](https://github.github.com/gh-aw/setup/cli/) · [Security architecture](https://github.github.com/gh-aw/introduction/architecture/) · [Safe outputs](https://github.github.com/gh-aw/reference/safe-outputs/) · [Cost management](https://github.github.com/gh-aw/reference/cost-management/)
- Releases: [gh-aw](https://github.com/github/gh-aw/releases)
- Companion skills: [github-actions](../ci-cd/GUIDE.md) (deterministic CI/CD and workflow linting), [github-issues](../../../github-issues/SKILL.md) and [github-pull-request](../../../github-pull-request/SKILL.md) (human-controlled GitHub writes), [mcp-setup](../../../mcp-setup/SKILL.md) (host MCP configuration).
