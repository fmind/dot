---
name: documentation-site
description: "Build Zensical docs and course sites: navigation, API docs, lessons, Pages, MkDocs/Hugo migration."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/documentation-site
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Documentation Sites

Use Zensical by default for project docs, courses, and blogs; keep an existing generator only when the project requires it or the user asks. [repository-docs](../repository-docs/SKILL.md) owns README and AGENTS consistency; [humanize](../humanize/SKILL.md) owns clear, scannable prose and Zensical visual blocks (`==mark==`, `!!!`/`???` admonitions, `===` tabs, grid cards — never GitHub `> [!IMPORTANT]`).

## Workflow

1. **Inspect the project**: preserve existing content, URLs, and publication rules. For MkDocs or Hugo sites, follow [migration](references/migration.md) instead of scaffolding over them.
1. **Bootstrap with a locked dependency**: check the [latest release](https://github.com/zensical/zensical/releases) and add Zensical as a dev dependency (run `zensical new` in scratch if `docs/` or `zensical.toml` exists, since it never overwrites):
   ```bash
   uv init --bare <slug> && cd <slug>
   uv add --dev 'zensical>=0.1.1,<0.2'
   uv run zensical new .
   ```
1. **Apply the starter**: copy [zensical.toml](templates/zensical.toml), [index.md](templates/index.md) (`docs/index.md`), `~/.agents/themes/zensical/fmind.css` (`docs/stylesheets/fmind.css`, or customer brand variables), and [abbreviations.md](templates/abbreviations.md) (`includes/abbreviations.md`); delete `docs/markdown.md`. Fill `<placeholder>` values, set `site_url` with its hosting prefix, and prune unused sections. See [configuration](references/configuration.md) for optional plugins.
1. **Write under `docs/`**: apply [humanize](../humanize/SKILL.md) plus one H1 per page, explicit `nav`, section `index.md` overviews, relative `.md` links, and frontmatter `description` ([authoring](references/authoring.md)). Courses start from the [lesson template](templates/lesson.md), prefer local exercises, and pair [VHS](../diagrams-as-code/references/recording/GUIDE.md) demos with a static fallback.
1. **Wire tasks and ignores**: merge [mise.toml](templates/mise.toml), ignore `site/` and `.cache/`, format with [dprint](../mise/references/dprint.md), and test examples per [python-stack](../python-stack/references/foundation/GUIDE.md).
1. **Validate**: `uv run --locked zensical build --clean --strict` must exit 0 with `No issues found`. Preview via `uv run --locked zensical serve -a 127.0.0.1:${PORT:-8000}` across nav, search, light/dark, 390 px mobile, keyboard, and copy buttons ([playwright](../playwright/SKILL.md)); run code and link checks separately.
1. **Publish**: replace `.github/workflows/docs.yml` with pinned [docs.yml](templates/docs.yml); enabling GitHub Pages or deploying requires publication authority.

## Gotchas

- **Read diagnostics from the top**: strict failures print `file:line:col` before tracebacks and emit ANSI colors even piped (`perl -pe 's/\e\[[0-9;]*m//g'` strips them).
- **Strict mode checks targets, not Markdown syntax**: unclosed fences and unknown icons build silently—inspect rendered pages.
- **Set `site_url` accurately**: `llmstxt` aborts without it; wrong prefixes break social cards, `llms.txt`, sitemaps, and instant navigation.
- **Keep Zensical locked and see [configuration](references/configuration.md#native-plugins) for build limits**: pre-1.0 (`0.1.x` beta) drops unsupported MkDocs Python plugins (`gen-files`, `hooks`) silently; `docs_dir` cannot be `.`, uv symlinks are unsupported, and `serve` lacks `--strict`.
- **Respect site branding**: the starter uses `~/.agents/DESIGN.md` tokens and Google Sans; keep existing/customer branding and generate Fmind visuals via [diagrams-as-code](../diagrams-as-code/SKILL.md).

## Documentation

- [Get started](https://zensical.org/docs/get-started/) · [Create a site](https://zensical.org/docs/create-your-site/) · [Configuration](https://zensical.org/docs/setup/basics/) · [Authoring](https://zensical.org/docs/authoring/markdown/)
- [Validation](https://zensical.org/docs/setup/validation/) · [Plugins](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Customization](https://zensical.org/docs/customization/) · [Publishing](https://zensical.org/docs/publish-your-site/)
- Source: [zensical/zensical](https://github.com/zensical/zensical) · [zensical/docs](https://github.com/zensical/docs) · Releases: [Zensical](https://github.com/zensical/zensical/releases)
- Official skills: none upstream in `zensical/zensical` or `zensical/docs` (checked 2026-10-31). [Zensical Studio](https://zensical.org/studio) (VS Code) adds a preview, formatter, linter, and link refactoring for Zensical and MkDocs projects.
