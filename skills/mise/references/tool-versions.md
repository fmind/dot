# Tool Versions

[upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades; this reference owns version pinning for new and existing projects.

## Workstation and projects

- **Workstation vs project scope**: `fmind/dot` `dot_config/mise/config.toml` tracks `latest` (with inline comments explaining holds like `python`) and resolves into `mise.lock`. Standalone projects pin fixed versions in their own `mise.toml` + `mise.lock`, never importing workstation config or moving when `fmind/dot` or sibling repos upgrade.
- **Use lockfile revision 4** (mise 2026.11.1+, recording npm provenance repos; run `mise lock --upgrade` once on older locks) alongside referenced lock graphs, and install with `--locked`.
- **Keep Python pin separate from `requires-python`**: align `.python-version` with the mise Python pin inside `requires-python`, and never add upper caps like `<3.15` to `requires-python` without a proven incompatibility (`uv` treats project `>=3.14,<3.15` as `==3.14.*` and ignores dependency upper caps; PEP 723 scripts may cap ranges to pick a compatible interpreter).
- **Replace template `latest` placeholders** with exact versions before installing or delivering a scaffolded project.

## Select exact versions

1. **Seed new projects from workstation locks** where tools overlap (parsed as TOML, never inferred from `latest` or `$PATH`), and resolve project-only tools to latest stable via `mise use --pin`.
1. **Upgrade existing projects independently** to latest stable on explicit request — never downgrade a newer project pin to match workstation or sibling versions.
1. **Match full backend identity**: tool, backend, install options, and platform (normalize duplicate aliases deliberately).
1. **Audit every declaration**: root, nested, env, and task tool pins plus CI/runtime version files, keeping compatibility holds as exact pins with documented failure evidence.

Record pins via mise (review and run `mise trust -y mise.toml` first if untrusted):

```bash
mise use --path mise.toml --pin <tool>@<exact-version>
mise lock
mise tasks validate
mise run all
```

## References

- [Configuration precedence](https://mise.jdx.dev/configuration.html) · [mise.lock](https://mise.jdx.dev/dev-tools/mise-lock.html) · [mise use](https://mise.jdx.dev/cli/use.html)
