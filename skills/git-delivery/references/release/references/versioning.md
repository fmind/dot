# Release Versioning Conventions

- **Let `git-cliff --bumped-version` compute versions**: override only for deliberate milestones like `v1.0.0`, and keep the `v` prefix (`vX.Y.Z`).
- **Pre-1.0 uses standard SemVer bumps** (`feat` → minor, breaking → `v1.0.0`) unless `[bump]` in `cliff.toml` sets `features_always_bump_minor = false` and `breaking_always_bump_major = false`.
- **Untagged repos start at `initial_tag`** (`v0.1.0` in global config).
- **Prove from remote state**: reconcile remote peeled tags, `release_sha` workflows, release flags, and assets rather than local tags or branch runs.
- **Pass `--config pyproject.toml` when using `[tool.git-cliff]`**: `git-cliff` checks project `cliff.toml` / `.cliff.toml` / `.config/cliff.toml` first, then `~/.config/git-cliff/cliff.toml`, which shadows `[tool.git-cliff]` unless `--config pyproject.toml` is explicit (verify via `Using configuration from:`).
