---
name: bootstrap
description: "Create a new repository: location, visibility, stack composition, shared layer, checks, and first push."
---

# Repository Bootstrap

Compose the selected foundation and application owner, then add the shared layer; [full-review][fr] owns recurring upkeep afterwards.

## Workflow

1. **Decide basics**: slug (lowercase, hyphens), owner, visibility (private by default), purpose, and target path (owner's configured workspace directory). Ask only for consequential unknowns.
1. **Compose stack & shared layer**: reuse supplied `mise.toml`, `lefthook.yml`, `.gitignore`, `.ignore`, `AGENTS.md`; pin tools via [mise][mise] (`mise use --path mise.toml --pin <tool>`) and commit `mise.lock`:

| Layer            | Guides & templates                                                                         | Pinned `mise.toml` tools                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| **Python / ML**  | [python][py] (`foundation`, `script`, `argparse`, web/UI), [mlops][ml]                     | `python`, `uv` (Ruff, ty, pytest, deptry in `pyproject.toml`)                                     |
| **Web / Agents** | [web-frontend][wf], [agent-frameworks][af] (`google-adk`, `mcp`/`a2a`/`acp`)               | Per stack                                                                                         |
| **Docs / IaC**   | [docs][docs], [infra-as-code][iac], [containers][ct], [gcloud][gc]                         | `trivy`, `opentofu`, `tflint`, `terraform-docs`, `kubectl`/`helm`, `typst`                        |
| **Repo core**    | [license][lic], [lefthook][lh], [project-setup][ps], [openspec][os], `cliff.toml`+`dprint` | `betterleaks`, `dprint`, `git-cliff`, `github:Fission-AI/OpenSpec`, `lefthook`, `lychee`, `typos` |
| **CI & sec**     | [ci-cd][ci], [dependabot][dep], [jactionlint][ja], [code-security][cs], [SECURITY][sec]    | `jactionlint`, `shellcheck` (`shfmt`, `vale` as needed)                                           |

- **Composition rules**: `Python + infra/ + docs/ + Dockerfile` keeps Python `mise.toml` as root; standalone doc sites use `docs.yml` instead of `ci.yml`; add root `SECURITY.md` only for custom scope or repos lacking `<owner>/.github/SECURITY.md` ([baseline][sb]).
- **OpenSpec default**: enable OpenSpec on new repos unless explicitly opted out—pin standalone `github:Fission-AI/OpenSpec` and `check:specs` in `mise.toml`, run `OPENSPEC_TELEMETRY=0 CI=1 openspec init --tools none --no-animation </dev/null`, and copy [config.yaml](../../openspec/templates/config.yaml) to `openspec/config.yaml` ([openspec][os]). When opted out, remove `github:Fission-AI/OpenSpec`, `OPENSPEC_TELEMETRY`, `[tasks."check:specs"]`, and `"check:specs"` from `check:local.depends` in `mise.toml`, drop `openspec` lines from `AGENTS.md`, and skip `openspec/`.

1. **Validate locally**: run `mise run install && mise run all`; qualify wheels and entry points for packages.
1. **Publish & ship when authorized**: commit (`chore: initial commit`, [commit messages][cm]), push via [repository][repo], release `v0.1.0` ([release][rel]), and deploy:

   ```bash
   gh repo create <owner>/<slug> --private --source . --push
   ```

1. **Done when**: `mise run all` (and CI) passes, `README.md`/`AGENTS.md` meet standards, and zero `<owner>`/`<slug>`/`<package>`/`<holder>`/`TODO` placeholders remain.

## Gotchas

- **Keep composed `AGENTS.md`**: merge app rules into foundation; never overwrite with `project-setup`'s template.
- **Never scaffold real secrets**: `.env.example` lists variable names only.

## Documentation

- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) · [Agent Skills](https://agentskills.io)

[af]: ../../agent-frameworks/SKILL.md
[ci]: ci-cd/GUIDE.md
[cm]: ../../git-delivery/SKILL.md#commit-messages
[cs]: ../../code-security/SKILL.md
[ct]: ../../containers/SKILL.md
[dep]: ../templates/dependabot.yml
[docs]: ../../docs/SKILL.md
[fr]: ../../full-review/SKILL.md
[gc]: ../../gcloud/SKILL.md
[iac]: ../../infra-as-code/SKILL.md
[ja]: ../templates/jactionlint.yaml
[lh]: ../../git-delivery/references/lefthook.md
[lic]: project-license/GUIDE.md
[mise]: ../../mise/SKILL.md
[ml]: ../../mlops/SKILL.md
[os]: ../../openspec/SKILL.md
[ps]: ../../agent-harnesses/references/project-setup.md
[py]: ../../python/SKILL.md
[rel]: ../../git-delivery/references/release/GUIDE.md
[repo]: repository/GUIDE.md
[sb]: repository/references/settings-baseline.md#gotchas
[sec]: ../templates/SECURITY.md
[wf]: ../../web-frontend/SKILL.md
