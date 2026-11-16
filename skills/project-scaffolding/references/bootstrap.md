---
name: bootstrap
description: "Create a new repository: location, visibility, stack composition, shared layer, checks, and first push."
---

# Repository Bootstrap

Compose the selected foundation and application owner, then add the shared repository layer; [full-review](../../full-review/SKILL.md) owns recurring upkeep afterwards.

## Workflow

1. **Decide basics**: slug (lowercase, hyphens), owner, visibility (private unless public requested), purpose, and directory (`~/fmind` for `fmind` repos). Ask only for consequential unknowns.
1. **Template ownership**: one-off repos need none; new templates use [Copier](copier.md) ([copier.yml](../templates/copier.yml)), and `.cruft.json` repos keep [Cookiecutter](cookiecutter.md).
1. **Compose the stack** (reusing supplied `mise.toml`, `lefthook.yml`, `.gitignore`, `.ignore`, `AGENTS.md`):
   - **Python**: [foundation](../../python-stack/references/foundation/GUIDE.md), [python-script](../../python-stack/references/python-script/GUIDE.md), [argparse](../../python-stack/references/argparse/GUIDE.md) CLI, or [python-mlops](../../python-mlops/references/ml-jobs.md).
   - **Web / UI**: Litestar API/DB ([litestar](../../python-web/references/litestar/references/bootstrap.md)), [fastapi](../../python-web/references/fastapi.md), [django](../../python-web/references/django/GUIDE.md), [gradio](../../python-web/references/gradio.md)/[nicegui](../../python-web/references/nicegui.md), or [web-frontend](../../web-frontend/SKILL.md) (+ [playwright](../../playwright/SKILL.md)).
   - **Agents & Protocols**: [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md), [google-adk](../../agent-frameworks/references/google-adk.md), [langgraph](../../agent-frameworks/references/langgraph.md)/[langchain](../../agent-frameworks/references/langchain.md); [mcp](../../agent-protocols/references/mcp/GUIDE.md), [a2a](../../agent-protocols/references/a2a.md), [acp](../../agent-protocols/references/acp.md).
   - **Docs, IaC, Containers**: [documentation-site](../../documentation-site/SKILL.md) (standalone `docs.yml` replaces `ci.yml`), [infra-as-code](../../infra-as-code/SKILL.md), [containerize](../../docker/references/containerize/GUIDE.md)/[cloud-run](../../cloud-run/SKILL.md)/[kubernetes](../../kubernetes/SKILL.md). Combining `Python + infra/ + docs/ + Dockerfile` keeps Python `mise.toml` as root, merges [in-app OpenTofu](../../infra-as-code/references/scaffold.md#opentofu-inside-an-application-repository), extends `zensical.toml` ([template](../../documentation-site/templates/zensical.toml)), and aligns [.dockerignore](../../docker/references/containerize/templates/.dockerignore).
1. **Add the shared layer** (skipping files already supplied):
   - `LICENSE`: [project-license](project-license/GUIDE.md); ignores: [update-ignores](../../full-review/references/update-ignores/GUIDE.md).
   - [dprint.json](../../mise/templates/dprint.json) ([dprint](../../mise/references/dprint.md)); hooks: [lefthook](../../github-actions/references/lefthook.md).
   - Security: `.betterleaks.toml` ([betterleaks.toml](../../code-security/templates/betterleaks.toml)) + `check:leaks`/`check:vuln`/`check:actions`; add [trivy.yaml](../../code-security/references/trivy/templates/trivy.yaml) + `check:scan` for containers, IaC, or non-`uv` locks ([code-security](../../code-security/references/code-review/GUIDE.md)).
   - CI/Dependabot: [ci-cd](../../github-actions/references/ci-cd/GUIDE.md), [dependabot.yml](../../github-actions/templates/dependabot.yml), and [jactionlint.yaml](../../github-actions/templates/jactionlint.yaml).
   - Agent & docs: `AGENTS.md` (when absent), `.agents/skills/`, `.claude/skills` (if Claude used) via [agent-project](../../agent-project/SKILL.md); `README.md` via [repository-docs](../../repository-docs/SKILL.md) ([README standard](../../repository-docs/references/readme.md)).
1. **Pin tools via [mise](../../mise/SKILL.md)**: replace `latest` with exact pins and commit lockfiles so the repo builds without `fmind/dot`.
1. **Validate locally**: `mise run install` and `mise run all` (including `check:leaks`); qualify wheels and entry points for packages.
1. **Publish & ship when authorized**: commit (`chore: initial commit`, [commit messages](../../git-delivery/SKILL.md#commit-messages)), push via [repository](../../gh/references/repository/GUIDE.md), release `v0.1.0` ([release](../../git-delivery/references/release/GUIDE.md)), and deploy ([cloud-run](../../cloud-run/SKILL.md)):

   ```bash
   gh repo create <owner>/<slug> --private --source . --push
   ```

1. **Done when**: `mise run all` (and CI) passes, `README.md`/`AGENTS.md` meet standards, and zero `<owner>`/`<slug>`/`<package>`/`<holder>`/`TODO` placeholders remain.

## Gotchas

- **Keep composed `AGENTS.md`**: merge application instructions into the foundation; never overwrite with `agent-project`'s generic template.
- **Never scaffold real secrets**: `.env.example` lists variable names only.

## Documentation

- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) · [Agent Skills](https://agentskills.io)
