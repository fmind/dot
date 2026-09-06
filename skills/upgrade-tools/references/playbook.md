# Upgrade Playbook

Per-manifest commands for the [upgrade-tools](../SKILL.md) workflow: bump, re-lock, validate with `mise run check` and `mise run test`, then move to the next ecosystem.

## mise (`mise.toml`, `mise.lock`)

Bump the pins and refresh the lockfile per the [mise skill](../../mise/SKILL.md) (`mise upgrade --bump`, then `mise lock`). One bump covers every backend-qualified tool in `mise.toml`, so it needs no separate ecosystem step.

## Python (`pyproject.toml`, `uv.lock`)

```sh
uv lock --upgrade                 # bump every locked dependency within its constraint
uv lock --upgrade-package <pkg>   # bump one package
uv sync                           # install the upgraded set
```

Raise `requires-python` and dependency floors in `pyproject.toml` by hand, only when a newer feature is needed; keep pre-1.0 tools range-pinned. See [python-stack](../../python-stack/SKILL.md).


## OpenTofu (`.terraform.lock.hcl`)

```sh
tofu init -upgrade                                                 # providers and modules within constraints
tofu providers lock -platform=linux_amd64 -platform=darwin_arm64   # platform hashes for CI
```

Validate with `tofu validate`, `tflint`, and `trivy config`. See [terraform](../../terraform/SKILL.md).

## Container images (`Dockerfile`)

Update the tag or digest of every `FROM` line to the latest stable from the image's registry (Chainguard, Docker Hub), rebuild with `mise run build`, and scan with `trivy image`. See [containerize](../../containerize/SKILL.md).

## GitHub Actions (`.github/workflows/*.yml`)

Resolve every action release to its full commit SHA and keep the human-readable version in a trailing comment (`owner/action@<sha> # vN.N.N`). Let [dependabot](../../dependabot/SKILL.md) propose SHA updates, verify the referenced tag before accepting them, and validate with `actionlint` plus `zizmor --offline`. See [github-actions](../../github-actions/SKILL.md).

## dprint (`dprint.json`)

```sh
dprint config update   # rewrite plugin URLs to the latest versions
```

Run it for each config (root and nested `extends`); validate with `dprint check`. See [dprint](../../dprint/SKILL.md).

## Agent skills

`skills update -p -y` where project-scoped external skills are installed; skip it in repositories that only author first-party skills.
