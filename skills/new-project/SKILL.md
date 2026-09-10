---
name: new-project
description: Bootstrap a new repository by composing the stack, license, mise, lefthook, dprint, CI, agent files, GitHub settings, and first release skills. Use when creating a project.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/new-project
  created: "2026-09-02"
  updated: "2026-09-10"
---

# New Project

Bootstrap a repository by composing the selected foundation and application owner, then adding the shared repository layer; [project-health](../project-health/SKILL.md) owns the recurring refresh afterwards.

## Workflow

1. **Decide the basics**: slug (lowercase, hyphens), owner, visibility, purpose, and parent directory. Default to `~/fmind` for personal `fmind` repositories, `~/fmind-ai` for `fmind-ai`, and `~/mlops-courses` for `mlops-courses`; ask only for consequential details not established by the task.
1. **Compose the selected stack**; finish its application profile before validation. Reuse the shared `mise.toml`, `lefthook.yml`, `.gitignore`, and project `AGENTS.md` where supplied:
   - Python library: [python-stack](../python-stack/SKILL.md) owns the minimal package and quality defaults.
   - Python CLI: the Python foundation, then [typer](../typer/SKILL.md) for application scaffolding and [cli-contracts](../cli-contracts/SKILL.md) for command behavior.
   - Litestar web app: the Python foundation, then [litestar](../litestar/SKILL.md) for the application, optional database integration, settings, and request tests.
   - Django web application: [django](../django/SKILL.md)
   - Python agent with the agents CLI: [agents-cli](../agents-cli/SKILL.md), then [google-adk](../google-adk/SKILL.md) for SDK code
   - Documentation or course site: [zensical](../zensical/SKILL.md), with [course-development](../course-development/SKILL.md) for lessons; infrastructure: [terraform](../terraform/SKILL.md)
1. **Add the shared layer**, skipping what the foundation or application owner already produced:
   - `LICENSE` and manifest field: [project-license](../project-license/SKILL.md)
   - `dprint.json`: [dprint](../dprint/SKILL.md); hooks installed: [lefthook](../lefthook/SKILL.md)
   - `trivy.yaml` plus the `check:*` scan tasks: [secure](../secure/SKILL.md)
   - `.github/workflows/ci.yml` and `security.yml`: [github-actions](../github-actions/SKILL.md); `.github/dependabot.yml`: [dependabot](../dependabot/SKILL.md)
   - `AGENTS.md`, `.agents/skills/`, and the `CLAUDE.md` bridge: [agent-project](../agent-project/SKILL.md); `README.md` and documentation: [repository-docs](../repository-docs/SKILL.md)
1. **Validate locally**: `mise run install` and `mise run all`; for Python packages also qualify the installed wheel and any command/module entry points through the selected stack. Before the first commit, `check:leaks` scans the working tree.
1. **Publish only within existing authorization**: when the user requested the initial commit and GitHub creation/push, create the remote after that commit (`chore: initial commit`, see [conventional-commit](../conventional-commit/SKILL.md)), then apply [github-repository](../github-repository/SKILL.md):

   ```bash
   gh repo create <owner>/<slug> --<visibility> --source . --push
   ```

1. **Ship when authorized**: a first `v0.1.0` through [release](../release/SKILL.md) once CI is green; a deploy target through [cloud-run](../cloud-run/SKILL.md) when the project serves traffic.
1. **Done when**:
   - `mise run all` is green locally; check CI for the resulting commit when a first push was authorized.
   - `README.md` says what the project is and how to run it; `AGENTS.md` says how agents work in it.
   - No scaffold placeholder (`<slug>`, `TODO`) remains in the delivered files; report pending publication separately.

## Gotchas

- **Keep the composed `AGENTS.md`**: merge the application owner's instructions into the foundation; agent-project's generic template must not overwrite the result.
- **Private data**: never scaffold with real secrets; `.env.example` documents names only.

## Documentation

- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) · [Agent Skills](https://agentskills.io)
- Companion skills: [project-health](../project-health/SKILL.md) (recurring refresh), [secure](../secure/SKILL.md) (security checklist), [mise](../mise/SKILL.md) (task vocabulary).
