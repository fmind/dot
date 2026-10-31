# Upgrade Playbook

Per-manifest commands for the [upgrade-tools](../SKILL.md) workflow: bump, re-lock, validate with `mise run check` and `mise run test`, then move to the next ecosystem.

## mise (`mise.toml`, `mise.lock`)

1. **Resolve latest stable releases** for the project's own tools; in `fmind/dot` use `mise run upgrade`, elsewhere preview with `mise outdated --bump --no-global`, then run `mise upgrade --bump --pin --no-global --no-prune`. `--no-global` keeps global tools unchanged, `--pin` writes exact versions for `latest` and prefix selectors, and `--no-prune` keeps the replaced versions, which mise otherwise deletes after `upgrade.prune_after` (24h by default). Exclude a justified hold with `--exclude <tool>`, preserve tool options, and regenerate the project's lock. Investigate a pin held below latest before moving it, and keep referenced interpreters available while virtual environments migrate.
1. **Keep runtime files coherent**: align `.python-version` and relevant CI/runtime pins with the selected mise versions, preserving intentional compatibility matrices. Recreate affected environments through the project's native package workflow; do not point an existing environment's interpreter symlink at a different Python minor version. Preserve declared support unless a change is justified.

After upgrading, preview cleanup of versions no configuration references:

```bash
mise ls --all-sources
mise prune --dry-run
```

Pruning retains tools referenced by tracked configs; external virtualenv links and running processes need a separate check. `dot prune mise` clears mise caches and is not installed-version pruning. On copy-on-write filesystems, summed directory footprints can count shared blocks more than once.

## Python (`pyproject.toml`, `uv.lock`)

```sh
uv lock --upgrade --dry-run       # preview every version change, majors included, without writing
uv lock --upgrade                 # bump every locked dependency within its constraint
uv lock --upgrade-package <pkg>   # bump one package
UV_MALWARE_CHECK=1 uv sync --locked --preview-features malware-check   # install the upgraded set, refusing known malware
```

Raise `requires-python` and dependency floors in `pyproject.toml` by hand, only when a newer feature is needed; keep pre-1.0 tools range-pinned.

- **Probe a new CPython minor before moving any pin**: remove any `requires-python` upper cap and run `uv lock` (otherwise `--locked` rejects the stale lock), then run `uv run --isolated --locked --no-build --python <next-minor> pytest -q -m "not integration"`. It fails on the first locked dependency without a wheel, so rerun after each fix; `filterwarnings = error` surfaces the minor's new deprecations. Use a final interpreter (uv warns when `--python` resolves to a pre-release). Move `.python-version`, the mise pin, and CI together only after the probe passes. See [python-stack](../../python-stack/references/foundation/GUIDE.md).

## OpenTofu (`.terraform.lock.hcl`)

```sh
tofu init -upgrade                                                 # providers and modules within constraints
tofu providers lock -platform=linux_amd64 -platform=darwin_arm64   # only for mirrors or non-OpenTofu registries
```

Validate with `tofu validate`, `tflint`, and `trivy config`. See [infra-as-code](../../infra-as-code/SKILL.md).

## Container images (`Dockerfile`)

Update the tag and digest of every `FROM` line, every `COPY --from=<image>`, and every other digest-pinned image reference (such as a testcontainers fixture like `POSTGRES_IMAGE` in the Litestar `conftest.py`) to the latest stable from the image's registry (Chainguard, Docker Hub), using the multi-platform index digest; rebuild with the project's image task, and scan the resulting local archive with `trivy --config trivy.yaml image --skip-dirs '' --input <image.tar>` or the published immutable `<registry>/<slug>@<digest>`. An image scan requires one of those targets. See [containerize](../../docker/references/containerize/GUIDE.md).

## GitHub Actions (`.github/workflows/*.yml`)

Resolve every action release to its full commit SHA and keep the human-readable version in a trailing comment (`owner/action@<sha> # vN.N.N`). Refresh SHAs here: [dependabot](../../github-actions/references/dependabot.md) runs security updates only, so it bumps a pin only for an advisory. Verify the referenced tag before accepting any SHA, and validate with `jactionlint`. See [github-actions](../../github-actions/references/ci-cd/GUIDE.md).

Dependabot cannot raise a `jdx/mise-action` `version:` input, and `mise run upgrade` never updates mise itself. The workstation updates its `mise` binary automatically (`self_update.auto = true`), while `fmind/dot`'s minimum tested `mise` pin is raised deliberately (`mise self-update <version>` when targeting a specific release): update the workflow `version:` pins (including the shipped github-actions, cloud-run, and documentation-site templates), `MINIMUM_MISE_VERSION` in `install.sh`, `min_version` in `mise.toml` and the python-stack and infra-as-code templates, and the README minimum together; a bootstrap test enforces that they agree. Read the release notes between versions for security fixes and lockfile changes first.

## dprint (`dprint.json`)

```sh
dprint config update --yes --recursive   # update root and nested configs without prompts
```

Validate with `dprint check`. See [dprint](../../dprint/SKILL.md).

## Agent skills

Refresh project-scoped external skills only per the [vendor-skill policy](../../agent-project/references/vendor-skills.md) (`DISABLE_TELEMETRY=1 skills update -p -y` in a clean candidate, then re-review); skip repositories that only author first-party skills.
