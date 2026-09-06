---
name: zensical
description: Write and build Markdown documentation and course sites with Zensical. Use for new docs sites, course publishing, or migrating Hugo and MkDocs content.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/zensical
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Zensical Documentation

Use Zensical as the default static publisher for documentation and courses; [course-development](../course-development/SKILL.md) owns learning design, executable labs, and acceptance.

## Workflow

1. **Inspect the project**: keep existing content, URLs, and publication rules; use [migration and authoring](references/authoring.md) when replacing Hugo or MkDocs.
1. **Bootstrap a new docs project** with a locked development dependency. In an existing Python project, skip `uv init`; in an existing docs tree, scaffold in a scratch directory and merge deliberately.
   ```bash
   uv init --bare <slug>
   cd <slug>
   uv add --dev zensical
   uv run zensical new .
   uv run zensical --version
   ```
1. **Configure `zensical.toml`**: set `project.site_name`, the real `site_url` including any repository prefix, explicit `nav`, and language. Keep generated Markdown extensions needed by the content; prefer small configuration changes over theme overrides.
1. **Write under `docs/`**: make `index.md` the entry point, use relative `.md` links, stable headings, fenced code with languages, and useful image descriptions. Use the [lesson template](references/lesson.md) for a new course page and the authoring reference for richer Markdown.
1. **Wire the repository tasks**: adapt [mise.toml](references/mise.toml) into the existing task graph. Use [dprint](../dprint/SKILL.md) for markup and [python-stack](../python-stack/SKILL.md) for executable examples.
1. **Preview and validate**:
   ```bash
   uv run zensical serve
   # In a separate terminal, or after stopping the preview:
   uv run zensical build --clean --strict
   ```
   Verify the rendered navigation, search, mobile layout, keyboard use, and code copying. Strict builds catch internal link and anchor warnings; run lesson examples and external link checks separately.
1. **Prepare publishing**: `site/` is the default output. Review the generated `.github/workflows/docs.yml`, route its build through the same locked mise tasks, and use [github-actions](../github-actions/SKILL.md) for action pins and permissions. Enable deployment only within the project's publication authority.

## Gotchas

- **Generated CI publishes**: `zensical new` creates a Pages workflow; inspect its triggers before including it in an existing repository.
- **Build output is disposable**: ignore `site/`, `.cache/`, and `.venv/`; retain `pyproject.toml`, `uv.lock`, configuration, and source content.
- **Plugin compatibility is explicit**: Zensical reimplements selected MkDocs plugins; check the supported list for the locked version before adding a plugin package.
- **Theme**: use Tokyo Night Moon colors through documented palette/CSS customization when theming; [fmind-visuals](../fmind-visuals/SKILL.md) owns Fmind illustrations and diagrams.
- **Reproducibility**: use `uv sync --locked` in CI and clean builds; verify the current stable release before upgrading. The local bootstrap and strict build were exercised with Zensical 0.0.59.

## Official Skills

No upstream authoring `SKILL.md` was found in `zensical/zensical` on 2026-09-06. This is the personal workflow; use the official documentation below for current capabilities.

## Documentation

- [Zensical](https://github.com/zensical/zensical) · [Create a site](https://zensical.org/docs/create-your-site/) · [Authoring](https://zensical.org/docs/authoring/markdown/)
- [Validation](https://zensical.org/docs/setup/validation/) · [Plugin compatibility](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Publishing](https://zensical.org/docs/publish-your-site/)
