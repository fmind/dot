---
name: bootstrap
description: "Repository bootstrap and stack composition."
---

# New Project

Bootstrap a repository by composing the selected foundation and application owner, then adding the shared repository layer; [repository-maintenance](../../repository-maintenance/SKILL.md) owns the recurring refresh afterwards.

## Workflow

1. **Decide the basics**: slug (lowercase, hyphens), owner, visibility, purpose, and parent directory. Default to private visibility; public resources require explicit user instruction. Default to `~/fmind` for personal `fmind` repositories, `~/fmind-ai` for `fmind-ai`, and `~/mlops-courses` for `mlops-courses`; ask only for consequential details not established by the task.
1. **Choose template ownership**: [Copier](copier.md) is the default when creating or maintaining a reusable project template. Keep existing Cookiecutter/Cruft projects on [their workflow](cookiecutter/GUIDE.md) unless migration is requested; a one-off repository does not require a new template.
1. **Compose the selected stack**; finish its application profile before validation. Reuse the shared `mise.toml`, `lefthook.yml`, `.gitignore`, and project `AGENTS.md` where supplied:
   - Python library: [python-stack](../../python-stack/references/foundation/GUIDE.md) owns the minimal package and quality defaults.
   - Python CLI: the Python foundation, then [typer](../../cli-development/references/typer/GUIDE.md) for application scaffolding and [cli-contracts](../../cli-development/references/cli-contracts.md) for command behavior.
   - Litestar web app: the Python foundation, then [litestar](../../python-web/references/litestar/GUIDE.md) for the application, optional database integration, settings, and request tests.
   - Django web application: [django](../../python-web/references/django/GUIDE.md)
   - Python agent with the agents CLI: [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md), then [google-adk](../../agent-frameworks/references/google-adk.md) for SDK code
   - Documentation or course site: [documentation-site](../../documentation-site/SKILL.md), with [course-development](../../course-development/SKILL.md) for lessons; infrastructure: [infra-as-code](../../infra-as-code/SKILL.md)
1. **Add the shared layer**, skipping what the foundation or application owner already produced:
   - `LICENSE` and manifest field: [project-license](project-license/GUIDE.md)
   - `dprint.json`: [dprint](../../dprint/SKILL.md); hooks installed: [lefthook](../../github-actions/references/lefthook.md)
   - `trivy.yaml` plus the `check:*` scan tasks: [security-review](../../security-review/references/code-review/GUIDE.md)
   - `.github/workflows/ci.yml` and `security.yml`: [github-actions](../../github-actions/references/ci-cd/GUIDE.md); `.github/dependabot.yml`: [dependabot](../../github-actions/references/dependabot.md)
   - `AGENTS.md`, `.agents/skills/`, and the `CLAUDE.md` bridge: [agent-project](../../agent-project/SKILL.md); `README.md` and documentation: [repository-docs](../../repository-docs/SKILL.md)
1. **Pin the toolchain** through [mise](../../mise/SKILL.md): replace scaffold selectors with exact versions from the workstation baseline for required tools, resolve project-only tools explicitly, and retain project-owned lockfiles. The new repository must install without the personal dotfiles checkout.
1. **Validate locally**: `mise run install` and `mise run all`; for Python packages also qualify the installed wheel and any command/module entry points through the selected stack. Before the first commit, `check:leaks` scans the working tree.
1. **Publish only within existing authorization**: when the user requested the initial commit and GitHub creation/push, create the remote after that commit (`chore: initial commit`, see [conventional-commit](../../git-delivery/references/conventional-commit.md)), then apply [github-repository](../../github-repository/SKILL.md):

   ```bash
   gh repo create <owner>/<slug> --private --source . --push
   ```

1. **Ship when authorized**: a first `v0.1.0` through [release](../../git-delivery/references/release/GUIDE.md) once CI is green; a deploy target through [cloud-run](../../cloud-run/SKILL.md) when the project serves traffic.
1. **Done when**:
   - `mise run all` is green locally; check CI for the resulting commit when a first push was authorized.
   - `README.md` says what the project is and how to run it; `AGENTS.md` says how agents work in it.
   - No scaffold placeholder (`<slug>`, `TODO`) remains in the delivered files; report pending publication separately.

## Gotchas

- **Keep the composed `AGENTS.md`**: merge the application owner's instructions into the foundation; agent-project's generic template must not overwrite the result.
- **Private data**: never scaffold with real secrets; `.env.example` documents names only.

## Documentation

- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) · [Agent Skills](https://agentskills.io)
- Companion skills: [repository-maintenance](../../repository-maintenance/SKILL.md) (recurring refresh), [security-review](../../security-review/references/code-review/GUIDE.md) (security checklist), [mise](../../mise/SKILL.md) (task vocabulary).
