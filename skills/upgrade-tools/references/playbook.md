# Upgrade Playbook

Per-manifest commands for the [upgrade-tools](../SKILL.md) workflow: bump, re-lock, validate with `mise run check` and `mise run test`, then move to the next ecosystem.

## mise (`mise.toml`, `mise.lock`)

Use the [shared tool baseline](../../mise/references/tool-versions.md). `fmind/dot` tracks `latest` by default, including Python. Every other owned repository records exact mise versions; running `mise upgrade --bump` independently everywhere defeats alignment.

1. **Discover repositories** under `~/fmind`, `~/fmind-ai`, and `~/mlops-courses`, plus the `fmind/dot` source. Inspect Git roots and instructions; include nested independent repositories, but exclude ignored vendor/build directories, disposable candidates, and archived snapshots. Canonicalize paths and identify linked worktrees so the same project is not upgraded twice. Report absent roots and excluded checkouts instead of silently claiming complete coverage.
1. **Record current state**: inspect each repository's status, staged and unstaged changes, mise declarations, lockfiles, and gate. `mise ls --all-sources --json` supplements filesystem discovery with references that retain installed versions; it does not replace discovery of repositories mise has never loaded. Include environment and task-specific declarations, backend aliases, and project runtime files in the comparison.
1. **Refresh the baseline** through the source-managed workflow in `fmind/dot`. Preserve uncommitted changes, resolve `latest` to stable releases, and capture the resulting managed lockfile. Validate its candidate before propagation; do not claim an untested source edit or the current shell's selection is an approved baseline. Keep referenced interpreters available while their virtual environments are being migrated. The repository's native upgrade task affects this workstation only; this skill performs the cross-repository work.
1. **Align each consumer** in a separate candidate where necessary. For shared tools, use the exact matching baseline resolution; for project-only tools, retain their exact lock resolution unless their upgrade was requested. Replace floating selectors with concrete versions, preserve tool options, and regenerate each project's own locks. Investigate newer consumer pins before proposing a downgrade. Do not add unrelated global tools to applications.
1. **Keep runtime files coherent**: align `.python-version` and relevant CI/runtime pins with the selected mise versions, preserving intentional compatibility matrices. Recreate affected environments through the project's native package workflow; do not point an existing environment's interpreter symlink at a different Python minor version. Update application dependencies only where required by the accepted migration, and preserve declared support unless a change is justified.
1. **Qualify adoption** with the repository's complete gate and relevant runtime smoke checks. Verify the tested candidate matches the transferred source and preserve staged selections. If a repository cannot adopt the baseline, leave its prior exact pin, document the incompatibility and failed check, and continue independent repositories. Repositories with pre-existing red gates remain unqualified until those failures are resolved.
1. **Finish with evidence**: report old and new tool versions, gate results, exceptions, unvisited repositories, and remaining duplicate installations. Commit, push, deploy, and delete installations only within the user's authorization. Do not have routine project builds read the personal baseline or rewrite sibling repositories.

For a selected consumer version, use native commands after inspecting its configuration (replace placeholders with the baseline's actual identity and version):

```bash
mise use --path mise.toml --pin <tool>@<exact-version>
mise lock
mise run all
```

After all possible consumers have adopted the baseline, preview cleanup:

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
tofu providers lock -platform=linux_amd64 -platform=darwin_arm64   # platform hashes for CI
```

Validate with `tofu validate`, `tflint`, and `trivy config`. See [infra-as-code](../../infra-as-code/SKILL.md).

## Container images (`Dockerfile`)

Update the tag or digest of every `FROM` line to the latest stable from the image's registry (Chainguard, Docker Hub), rebuild with `mise run build`, and scan with `trivy --config trivy.yaml image --skip-dirs ''`. See [containerize](../../containerize/references/image-build/GUIDE.md).

## GitHub Actions (`.github/workflows/*.yml`)

Resolve every action release to its full commit SHA and keep the human-readable version in a trailing comment (`owner/action@<sha> # vN.N.N`). Let [dependabot](../../github-actions/references/dependabot.md) propose SHA updates, verify the referenced tag before accepting them, and validate with `actionlint` plus `zizmor --offline`. See [github-actions](../../github-actions/references/ci-cd/GUIDE.md).

## dprint (`dprint.json`)

```sh
dprint config update   # rewrite plugin URLs to the latest versions
```

Run it for each config (root and nested `extends`); validate with `dprint check`. See [dprint](../../dprint/SKILL.md).

## Agent skills

`skills update -p -y` where project-scoped external skills are installed; skip it in repositories that only author first-party skills.
