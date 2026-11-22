---
name: bootstrap
description: "Create a new repository: location, visibility, stack composition, shared layer, checks, and first push."
---

# Repository Bootstrap

Compose the selected foundation and application owner, then add the shared repository layer; [full-review](../../full-review/SKILL.md) owns recurring upkeep afterwards.

## Workflow

1. **Decide basics**: slug (lowercase, hyphens), owner, visibility (private unless public requested), purpose, and directory (`~/fmind` for `fmind` repos). Ask only for consequential unknowns.
1. **Compose the stack** (reusing supplied `mise.toml`, `lefthook.yml`, `.gitignore`, `.ignore`, `AGENTS.md`):
   - **Python**: [foundation](../../python/references/foundation/GUIDE.md) (`LicenseRef-Proprietary` default; opt in to Zensical docs or `-m integration` only when needed), [python/script](../../python/references/script/GUIDE.md), [argparse](../../python/references/argparse/GUIDE.md) CLI, or [mlops/ml-jobs](../../mlops/references/ml-jobs.md).
   - **Web / UI**: Litestar API/DB ([litestar](../../python/references/litestar/references/bootstrap.md)), [fastapi](../../python/references/fastapi.md), [django](../../python/references/django/GUIDE.md), [python/ui](../../python/references/ui.md) (Gradio/NiceGUI), or [web-frontend](../../web-frontend/SKILL.md) (+ [playwright](../../web-frontend/references/playwright.md)).
   - **Agents & Protocols**: [google-adk](../../agent-frameworks/references/google-adk.md) (default), [langgraph](../../agent-frameworks/references/langgraph.md)/[langchain](../../agent-frameworks/references/langchain.md), [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md) (opt-in wrapper); [mcp](../../agent-frameworks/references/mcp/GUIDE.md), [a2a](../../agent-frameworks/references/a2a.md), [acp](../../agent-frameworks/references/acp.md).
   - **Docs, IaC, Containers**: [docs/site](../../docs/references/site/GUIDE.md) (standalone `docs.yml` replaces `ci.yml`; Python libraries opt in), [infra-as-code](../../infra-as-code/SKILL.md), [containerize](../../containers/references/containerize/GUIDE.md)/[cloud-run](../../gcloud/references/cloud-run/GUIDE.md)/[kubernetes](../../containers/references/kubernetes/GUIDE.md). Combining `Python + infra/ + docs/ + Dockerfile` keeps Python `mise.toml` as root, merges [in-app OpenTofu](../../infra-as-code/references/scaffold.md#opentofu-inside-an-application-repository), extends `zensical.toml` ([template](../../docs/references/site/templates/zensical.toml)), and aligns [.dockerignore](../../containers/references/containerize/templates/.dockerignore).
1. **Add the shared layer** (skipping files already supplied):
   - `LICENSE`: [project-license](project-license/GUIDE.md); ignores: [update-ignores](../../full-review/references/update-ignores/GUIDE.md).
   - [dprint.json](../../mise/templates/dprint.json) ([dprint](../../mise/references/dprint.md)); hooks: [lefthook](lefthook.md).
   - Security: `.betterleaks.toml` ([betterleaks.toml](../../code-security/templates/betterleaks.toml)) + `check:leaks`/`check:vuln`/`check:actions`; add [trivy.yaml](../../code-security/references/trivy/templates/trivy.yaml) + `check:scan` for containers, IaC, or non-`uv` locks ([code-security](../../code-security/references/code-review/GUIDE.md)).
   - CI/Dependabot: [ci-cd](ci-cd/GUIDE.md), [dependabot.yml](../templates/dependabot.yml), and [jactionlint.yaml](../templates/jactionlint.yaml).
   - Agent & docs: `AGENTS.md` (when absent) and `.agents/skills/` via [project-setup](../../agent-harnesses/references/project-setup.md); `README.md` via [docs/repository](../../docs/references/repository/GUIDE.md) ([README standard](../../docs/references/repository/references/readme.md)).
1. **Pin tools via [mise](../../mise/SKILL.md)**: replace `latest` with exact pins (`mise use --path mise.toml --pin <tool>`) and commit `mise.lock` so the repo builds without `fmind/dot` (never assume repo CI/release tools live globally):
   - **All repos**: `betterleaks`, `dprint`, `git-cliff`, `jactionlint`, `lefthook`, `lychee`, `typos` (add `trivy` for containers, IaC, or non-`uv` locks; `shellcheck` + `shfmt` when shipping shell scripts; `vale` for public docs).
   - **Python**: `python`, `uv` (Ruff, ty, pytest, deptry live in `pyproject.toml` `[dependency-groups]` dev).
   - **OpenTofu / K8s**: `opentofu`, `tflint`, `terraform-docs` (`kubectl`, `helm`, `kustomize`, `kubeconform` for K8s).
   - **Typst decks / Docs**: `typst` (or `zensical` in `uv` dev deps for doc sites).
1. **Validate locally**: `mise run install` and `mise run all` (including `check:leaks`); qualify wheels and entry points for packages.
1. **Publish & ship when authorized**: commit (`chore: initial commit`, [commit messages](../../git-delivery/SKILL.md#commit-messages)), push via [repository](repository/GUIDE.md), release `v0.1.0` ([release](../../git-delivery/references/release/GUIDE.md)), and deploy ([cloud-run](../../gcloud/references/cloud-run/GUIDE.md)):

   ```bash
   gh repo create <owner>/<slug> --private --source . --push
   ```

1. **Done when**: `mise run all` (and CI) passes, `README.md`/`AGENTS.md` meet standards, and zero `<owner>`/`<slug>`/`<package>`/`<holder>`/`TODO` placeholders remain.

## Gotchas

- **Keep composed `AGENTS.md`**: merge application instructions into the foundation; never overwrite with `project-setup`'s generic template.
- **Never scaffold real secrets**: `.env.example` lists variable names only.

## Documentation

- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) · [Agent Skills](https://agentskills.io)
