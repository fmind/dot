# Release Versioning Conventions

- **git-cliff owns the version**: let `git-cliff --bumped-version` decide; override only for a deliberate bump such as the first stable `v1.0.0`.
- **Keep the `v` tag prefix**: git-cliff and `gh` use `vX.Y.Z`; keep the `v`.
- **Pre-1.0 follows the same rules**: git-cliff applies the same rules below `v1.0.0`, so a `feat` bumps the minor and a breaking change jumps to `v1.0.0`.
- **Opt into a tolerant 0.x line**: set `features_always_bump_minor = false` and `breaking_always_bump_major = false` under `[bump]` in `cliff.toml`.
- **First release starts at `initial_tag`**: with no tag yet, git-cliff starts from the configured `initial_tag` (`v0.1.0` in the global config).
- **Prove releases from remote state**: a local tag, a green local gate, a draft release, or a latest-branch run proves nothing about the published release; reconcile the remote tag, exact-head workflows, state, and assets.
- **Repository `cliff.toml` precedes global**: git-cliff reads `cliff.toml` from the repository root or falls back to `~/.config/git-cliff/cliff.toml`; `--config` only forces another file.
