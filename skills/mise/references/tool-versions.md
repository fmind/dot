# Tool Versions

[upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades; this reference owns version selection for new and existing projects.

## Workstation and projects

- **The workstation config owns only the workstation**: fmind/dot's `dot_config/mise/config.toml` owns requests and options, and the adjacent `mise.lock` owns exact resolutions. It tracks `latest` by default; an intentional compatibility or release-channel hold (such as `python`) carries its reason in the comment beside its declaration, so read the reason there.
- **Lock with revision 4 bundles**: use lockfile revision 4 (mise 2026.11.1+; it also records npm provenance repositories) and keep each lockfile with its referenced native dependency files. `mise lock --upgrade` migrates an older lockfile once; mise otherwise keeps a lockfile's revision. Install with `--locked` and validate fresh installations after graph updates; in fmind/dot, the project `AGENTS.md` owns the workstation lock tasks.
- **Projects own their pins**: other repositories under `~/fmind` declare fixed mise versions with their own lockfiles and change them only during their own requested upgrade. A workstation or sibling upgrade never changes them, and neither do their application dependencies. Use only the tools each project needs. Do not import or symlink personal configuration into a project or require this checkout in its CI.
- **Separate runtime pins from `requires-python`**: pin Python like every other mise tool; when present, `.python-version` selects the one development interpreter, so align it with that pin and keep it within `requires-python`. Keep `requires-python` as the package's supported range; a newer interpreter pin does not automatically raise its minimum or drop tested interpreters. Do not cap `requires-python` (such as `<3.15`) without a verified incompatibility noted beside it: uv reads a project's `>=3.14,<3.15` as `==3.14.*` and refuses newer interpreters, and it ignores caps in dependencies anyway. A PEP 723 script may cap the range so uv selects a compatible interpreter.
- **Treat template `latest` as a placeholder**: `latest` in a reusable scaffold is a selection placeholder. Replace it with an exact version before installing or delivering a project; template examples are not a second version catalog.

## Select exact versions

1. **Seed new projects from installed versions**: when creating a project, prefer the workstation's locked version of each required tool it also installs, so installations are reused; resolve project-only tools to their current stable release with `mise use --pin`. Read lock data with TOML tooling; do not execute the template or infer versions from `latest` or the active shell. The seed is a starting point, not a binding.
1. **Upgrade existing projects on their own request**: resolve the current stable release of the project's own tools during that project's upgrade; never downgrade a newer project pin to match the workstation or a sibling.
1. **Match full installation identity**: tool, backend, install options, and target platform. Normalize equivalent aliases deliberately when they would create duplicate installations; preserve required options and verify the selected backend. Matching version strings alone does not establish identical installations.
1. **Cover every project declaration**: check root, nested, environment-specific, and task-level tool declarations that belong to the project, along with relevant CI and runtime version files. Preserve intentional test matrices and platform-specific requirements. A genuine incompatibility stays as an exact pin with a concise reason and the failed validation evidence.

Use the installed CLI's native explicit target when recording a selected version:

```bash
mise use --path mise.toml --pin <tool>@<exact-version>
mise lock
mise tasks validate
mise run all
```

`mise use` installs missing tools as well as editing configuration. Inspect diffs and resolve backend ambiguity before invoking it. If a new config is untrusted, review it and run `mise trust -y mise.toml` before retrying. Normal installations consume the recorded versions; an upgrade is an explicit operation.

## References

- [Configuration precedence](https://mise.jdx.dev/configuration.html) · [mise.lock](https://mise.jdx.dev/dev-tools/mise-lock.html) · [mise use](https://mise.jdx.dev/cli/use.html)
