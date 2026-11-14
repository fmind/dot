---
name: bootstrap
description: "Create a new repository: location, visibility, stack composition, shared layer, checks, and first push."
---

# Repository Bootstrap

Compose the selected foundation and application owner, then add the shared repository layer; [full-review](../../full-review/SKILL.md) owns recurring upkeep afterwards.

## Workflow

1. **Decide basics**: slug (lowercase, hyphens), owner, visibility (private unless public is explicitly requested), purpose, and parent directory (`~/fmind` for personal `fmind` repos). Ask only for consequential unknowns.
1. **Choose template ownership**: one-off repos need no template. Reusable templates default to [Copier](copier.md); existing Cookiecutter/Cruft projects stay on [their workflow](cookiecutter.md) unless migration is requested.
1. **Compose the stack** and finish its application profile before validation, reusing supplied `mise.toml`, `lefthook.yml`, `.gitignore`, `.ignore`, and `AGENTS.md`:
   - Python library: [python-stack](../../python-stack/references/foundation/GUIDE.md).
   - Python CLI: Python foundation + [argparse](../../python-stack/references/argparse/GUIDE.md) (stdlib default; add Typer when rich subcommands/help warrant it).
   - Litestar web app: Python foundation + [litestar](../../python-web/references/litestar/GUIDE.md).
   - Django web app: [django](../../python-web/references/django/GUIDE.md).
   - Python agent (`agents` CLI): [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md), then [google-adk](../../agent-frameworks/references/google-adk.md).
   - Docs/course site: [documentation-site](../../documentation-site/SKILL.md); infrastructure: [infra-as-code](../../infra-as-code/SKILL.md).
1. **Add the shared layer**, skipping files already produced by the stack owner:
   - `LICENSE` + manifest field: [project-license](project-license/GUIDE.md).
   - `.ignore` for Neovim search (fixtures, snapshots, generated data, minified assets; never Python sources, which Ruff and `ty` would skip): [update-ignores](../../full-review/references/update-ignores/GUIDE.md).
   - `dprint.json`: [dprint](../../mise/references/dprint.md); hooks: [lefthook](../../github-actions/references/lefthook.md).
   - Security checks: `check:leaks` + `check:vuln` + `check:actions` for pure-Python repos; add `trivy.yaml` + `check:scan` when the repo ships containers, IaC, or non-`uv` lockfiles per [code-security](../../code-security/references/code-review/GUIDE.md).
   - `.github/workflows/{ci,security}.yml`: [github-actions](../../github-actions/references/ci-cd/GUIDE.md); `.github/dependabot.yml`: [dependabot](../../github-actions/references/dependabot.md).
   - `AGENTS.md` (only when no stack template supplied one), `.agents/skills/`, and `.claude/skills` (only when Claude Code is used): [agent-project](../../agent-project/SKILL.md); `README.md` and docs: [repository-docs](../../repository-docs/SKILL.md).
1. **Apply the [README standard](../../repository-docs/references/readme.md)**: SVG logo, clear audience/outcome, badges backed by live resources (omit unpublished ones), and a verified quickstart; link deep references instead of bloating `README.md`.
1. **Pin tools via [mise](../../mise/SKILL.md)**: replace scaffold selectors with exact versions (seeded from workstation locks where shared), resolve project-only tools, and commit project lockfiles so the repo installs without `fmind/dot`.
1. **Validate locally**: `mise run install` and `mise run all` (including `check:leaks` before first commit); for Python packages, qualify the built wheel and entry points.
1. **Publish only when authorized**: commit (`chore: initial commit`, per [commit messages](../../git-delivery/SKILL.md#commit-messages)), create the remote, then apply [repository](../../gh/references/repository/GUIDE.md):

   ```bash
   gh repo create <owner>/<slug> --private --source . --push
   ```

1. **Ship when authorized**: `v0.1.0` via [release](../../git-delivery/references/release/GUIDE.md) once CI is green; deploy via [cloud-run](../../cloud-run/SKILL.md) when serving traffic.
1. **Done when**: `mise run all` (and CI if pushed) passes, `README.md` and `AGENTS.md` meet acceptance criteria, and zero `<slug>`/`<package>`/`<holder>`/`TODO` placeholders remain (report pending publication separately).

## Gotchas

- **Keep composed `AGENTS.md`**: merge application instructions into the foundation; never overwrite with `agent-project`'s generic template.
- **Never scaffold real secrets**: `.env.example` lists variable names only.

## Documentation

- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) · [Agent Skills](https://agentskills.io)
