# Upgrade Playbook

Per-ecosystem commands for [upgrade-tools](../SKILL.md): bump, re-lock, pass `mise run check` and `mise run test`, then advance.

## mise (`mise.toml`, `mise.lock`)

1. **Bump project tools**: run `mise run upgrade` in `fmind/dot`; elsewhere preview `mise outdated --bump --no-global`, then run `mise upgrade --bump --pin --no-global --no-prune` (`--no-prune` keeps prior installs past `upgrade.prune_after`'s 24h default while venvs migrate; pass `--exclude <tool>` for documented holds) and `mise lock`.
1. **Sync runtime files**: align `.python-version` and CI pins with `mise.toml` (preserving intentional test matrices), and recreate `.venv` cleanly rather than repointing Python minor symlinks.

Preview unreferenced installs afterwards (`dot prune mise` cleans cache files only, not installed versions, and external venv symlinks or running processes may still reference untracked installs):

```bash
mise ls --all-sources
mise prune --dry-run
```

## Python (`pyproject.toml`, `uv.lock`)

```sh
uv lock --upgrade --dry-run       # preview version bumps (including majors)
uv lock --upgrade                 # bump all locked packages within constraints
uv lock --upgrade-package <pkg>   # bump one package
UV_MALWARE_CHECK=1 uv sync --locked --preview-features malware-check
```

Raise `requires-python` or dependency floors manually only when new features are needed; keep `0.x` packages range-bounded.

- **Probe new CPython minors before moving pins**: drop any `requires-python` upper cap, run `uv lock`, and test `uv run --isolated --locked --no-build --python <next-minor> pytest -q -m "not integration"` on a final release (fixing missing wheels and `filterwarnings = error` deprecations) before updating `.python-version`, `mise.toml`, and CI ([python-stack](../../python-stack/references/foundation/GUIDE.md)).

## OpenTofu (`.terraform.lock.hcl`)

```sh
tofu init -upgrade
tofu providers lock -platform=linux_amd64 -platform=darwin_arm64   # only for mirrors or non-OpenTofu registries
```

Validate with `tofu validate`, `tflint`, and `trivy config` ([infra-as-code](../../infra-as-code/SKILL.md)).

## Container images (`Dockerfile`)

Refresh tag + multi-platform index `@sha256:` digest on every `FROM`, `COPY --from=<image>`, and test fixture image (e.g. `POSTGRES_IMAGE` in `conftest.py`), rebuild via `build:image`, and scan with `trivy --config trivy.yaml image --skip-dirs '' --input <image.tar>` (or `<registry>/<slug>@<digest>`) per [containerize](../../docker/references/containerize/GUIDE.md).

## GitHub Actions (`.github/workflows/*.yml`)

Resolve latest release tags to verified 40-hex commit SHAs (`owner/action@<sha> # vN.N.N`) and run `jactionlint --profile pedantic` ([dependabot](../../github-actions/references/dependabot.md) bumps vulnerable pins only; see [ci-cd](../../github-actions/references/ci-cd/GUIDE.md)).

Raising the tested `mise` floor in `fmind/dot` (`self_update.auto = "24h"` updates the workstation binary, while `mise run upgrade` skips mise itself; use `mise self-update <version>` for an exact target) requires updating workflow `version:` inputs (including `github-actions`, `cloud-run`, and `documentation-site` templates), `MINIMUM_MISE_VERSION` in `install.sh`, `min_version` in `mise.toml` plus `python-stack`, `infra-as-code`, and `documentation-site` templates, and `README.md` together after checking release notes (`test_bootstrap.py` enforces parity).

## dprint (`dprint.json`)

```sh
dprint config update --yes --recursive
```

Pass the project's cooldown flag (e.g. `--minimum-dependency-age P7D`) when configured, then run `dprint check` ([dprint](../../mise/references/dprint.md)).

## Agent skills

Update project-scoped vendor skills only per [vendor-skill policy](../../agent-project/references/vendor-skills.md) (`DISABLE_TELEMETRY=1 skills update -p -y` in a clean snapshot, followed by review).
