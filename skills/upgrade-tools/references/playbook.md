# Upgrade Playbook

Per-manifest commands for the [upgrade-tools](../SKILL.md) workflow: bump, re-lock, validate with `mise run check` and `mise run test`, then move to the next ecosystem.

## mise (`mise.toml`, `mise.lock`)

1. **Record current state**: inspect the repository's status, staged and unstaged changes, mise declarations (root, nested, environment, and task-level), backend aliases, lockfiles, runtime files, and gate.
1. **Resolve latest stable releases** for the project's own tools; in `fmind/dot` use `mise run upgrade`. Replace floating selectors with exact versions using the [exact-pin commands](../../mise/references/tool-versions.md#select-exact-versions), preserve tool options, and regenerate the project's lock. Investigate a pin held below latest before moving it, and keep referenced interpreters available while virtual environments migrate.
1. **Keep runtime files coherent**: align `.python-version` and relevant CI/runtime pins with the selected mise versions, preserving intentional compatibility matrices. Recreate affected environments through the project's native package workflow; do not point an existing environment's interpreter symlink at a different Python minor version. Preserve declared support unless a change is justified.
1. **Qualify the upgrade** with the repository's complete gate and relevant runtime smoke checks. Verify the tested candidate matches the source and preserve staged selections. If the upgrade cannot be qualified, keep the prior exact pin and document the incompatibility and failed check. A pre-existing red gate leaves the repository unqualified until it is resolved.
1. **Finish with evidence**: report old and new tool versions, gate results, and exceptions. Commit, push, deploy, and delete installations only within the user's authorization. Do not have project builds read the personal workstation configuration.

After upgrading, preview cleanup of versions no configuration references:

```bash
mise ls --all-sources
mise prune --dry-run
```

Pruning retains tools referenced by tracked configs; external virtualenv links and running processes need a separate check. `dot prune mise` clears mise caches and is not installed-version pruning. On copy-on-write filesystems, summed directory footprints can count shared blocks more than once.

## Python (`pyproject.toml`, `uv.lock`)

```sh
uv lock --upgrade                 # bump every locked dependency within its constraint
uv lock --upgrade-package <pkg>   # bump one package
uv sync                           # install the upgraded set
```

Raise `requires-python` and dependency floors in `pyproject.toml` by hand, only when a newer feature is needed; keep pre-1.0 tools range-pinned. See [python-stack](../../python-stack/references/foundation/GUIDE.md).

## OpenTofu (`.terraform.lock.hcl`)

```sh
tofu init -upgrade                                                 # providers and modules within constraints
tofu providers lock -platform=linux_amd64 -platform=darwin_arm64   # only for mirrors or non-OpenTofu registries
```

Validate with `tofu validate`, `tflint`, and `trivy config`. See [infra-as-code](../../infra-as-code/SKILL.md).

## Container images (`Dockerfile`)

Update the tag or digest of every `FROM` line to the latest stable from the image's registry (Chainguard, Docker Hub), rebuild with the project's image task, and scan the resulting local archive with `trivy --config trivy.yaml image --skip-dirs '' --input <image.tar>` or the published immutable `<registry>/<slug>@<digest>`. An image scan requires one of those targets. See [containerize](../../containerize/SKILL.md).

## GitHub Actions (`.github/workflows/*.yml`)

Resolve every action release to its full commit SHA and keep the human-readable version in a trailing comment (`owner/action@<sha> # vN.N.N`). Let [dependabot](../../github-actions/references/dependabot.md) propose SHA updates, verify the referenced tag before accepting them, and validate with `actionlint` plus `zizmor --offline`. See [github-actions](../../github-actions/references/ci-cd/GUIDE.md).

Dependabot cannot raise a `jdx/mise-action` `version:` input, and `mise run upgrade` never updates mise itself. In `fmind/dot`, update mise deliberately: `mise self-update <version>` on the workstation, then raise the workflow `version:` pins (including the shipped github-actions and cloud-run templates), `MINIMUM_MISE_VERSION` in `install.sh`, `min_version` in `mise.toml` and the python-stack and infra-as-code templates, and the README minimum together; a bootstrap test enforces that they agree. Read the release notes between versions for security fixes and lockfile changes first.

## dprint (`dprint.json`)

```sh
dprint config update --yes   # update reviewed plugins without interactive prompts
```

Run it for each config (root and nested `extends`); validate with `dprint check`. See [dprint](../../dprint/SKILL.md).

## Agent skills

`skills update -p -y` where project-scoped external skills are installed; skip it in repositories that only author first-party skills.
