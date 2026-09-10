# Python Tooling Ownership

The shared [manifest](pyproject.toml.template) and [tasks](mise.toml) form one usable baseline. Keep their Python-specific configuration together; use the owning skill for commands, diagnostics, and optional integrations.

- [uv](../../uv/SKILL.md) owns dependencies, environments, interpreter selection, lockfiles, and build-backend compatibility.
- [ruff](../../ruff/SKILL.md) and [ty](../../ty/SKILL.md) own lint, formatting, and type-checking procedures.
- [mise](../../mise/SKILL.md) owns the task vocabulary; [lefthook](../../lefthook/SKILL.md) owns when hooks invoke tasks; [dprint](../../dprint/SKILL.md) owns markup and configuration formatting.
- [test-driven-development](../../test-driven-development/SKILL.md) owns regression and property-testing procedures. The shared pytest configuration keeps tests offline and warnings visible; specialists supply framework fixtures and optional integration setup.
- [secure](../../secure/SKILL.md) owns repository security checks, including dependency, secret, and configuration scans.
- [pydantic](../../pydantic/SKILL.md) owns validation and settings implementation; [observability](../../observability/SKILL.md) owns structured logging and trace correlation.

Version constraints in templates are a baseline, not a latest-release claim. Preserve a project's supported range and lock policy; use [upgrade-tools](../../upgrade-tools/SKILL.md) when upgrades are requested.
