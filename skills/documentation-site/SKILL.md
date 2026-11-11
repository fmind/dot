---
name: documentation-site
description: "Build Zensical docs and course sites: navigation, API docs, lessons, Pages, MkDocs/Hugo migration."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/documentation-site
  created: "2026-09-16"
  updated: "2026-11-10"
---

# Documentation Sites

Use Zensical by default for project docs, courses, and blogs; keep an existing generator only when the project requires it or the user asks. [repository-docs](../repository-docs/SKILL.md) owns README and AGENTS consistency.

## Workflow

1. **Inspect the project**: preserve existing content, URLs, and publication rules. For MkDocs or Hugo sites, follow [migration](references/migration.md) instead of scaffolding over them.
1. **Bootstrap with a locked dependency**: check the [latest release](https://github.com/zensical/zensical/releases) and add Zensical as a dev dependency (skip `uv init` in existing Python projects; run `zensical new` in a scratch directory when `docs/` or `zensical.toml` exists, since it never overwrites):
   ```bash
   uv init --bare <slug> && cd <slug>
   uv add --dev 'zensical>=0.1.0,<0.2'
   uv run zensical new .
   ```
1. **Apply the starter**: copy [zensical.toml](templates/zensical.toml), [index.md](templates/index.md) (`docs/index.md`), `~/.agents/themes/zensical/fmind.css` (`docs/stylesheets/fmind.css`, or customer brand variables), and [abbreviations.md](templates/abbreviations.md) (`includes/abbreviations.md`); delete `docs/markdown.md`. Fill `<placeholder>` values, set `site_url` with its hosting prefix, and prune unused sections. See [configuration](references/configuration.md) for starter defaults and optional plugins (blog, tags, redirects, API docs, versions, offline).
1. **Write under `docs/`**: one H1 per page, explicit `nav`, section `index.md` overviews, relative `.md` links, and frontmatter `description` ([authoring](references/authoring.md)). Courses start from the [lesson template](templates/lesson.md), prefer local exercises (live models/cloud need authority and budget), and pair [VHS](../fmind-visuals/references/recording.md) demos with a static fallback.
1. **Wire tasks and ignores**: merge [mise.toml](templates/mise.toml), ignore `site/` and `.cache/`, format Markdown with [dprint](../mise/references/dprint.md), and test executable examples per [python-stack](../python-stack/references/foundation/GUIDE.md).
1. **Validate**: `uv run --locked zensical build --clean --strict` must exit 0 with `No issues found`. Preview via `uv run --locked zensical serve` (`localhost:8000`) across navigation, search, light/dark palettes, 390 px width, keyboard, and code copy (screenshot with [playwright](../playwright/SKILL.md)); run lesson code and external link checks separately.
1. **Publish**: replace `.github/workflows/docs.yml` with pinned [docs.yml](templates/docs.yml) ([github-actions](../github-actions/references/ci-cd/GUIDE.md) owns pins); enabling GitHub Pages or deploying requires publication authority.

## Gotchas

- **Read diagnostics from the top**: strict failures print `file:line:col` before the Python traceback, and keep ANSI colors when piped (`NO_COLOR` ignored; strip with `perl -pe 's/\e\[[0-9;]*m//g'`).
- **Strict mode misses syntax errors**: missing pages, anchors, snippets (`check_paths`), and autorefs fail, but unclosed fences and unknown icons build silently—inspect rendered pages.
- **`site_url` is load-bearing**: `llmstxt` aborts without it, and wrong prefixes break social cards, `llms.txt`, sitemaps, and instant navigation.
- **Unsupported MkDocs plugins fail silently**: Zensical never runs MkDocs Python plugins; verify against the [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/). `gen-files` and `hooks` are unsupported; `exclude_docs`, `draft_docs`, and `not_in_nav` require Zensical ≥0.0.70.
- **Check feature interactions and privacy**: mutually exclusive features, offline limits, and third-party font/Mermaid/analytics hosts live in [configuration](references/configuration.md).
- **Layout and CLI limits**: `docs_dir` cannot be `.`; uv symlink mode is unsupported; `serve` lacks `--strict` and fails on busy ports with `Address already in use` (use `-a 127.0.0.1:<port>`).
- **Keep Zensical locked**: pre-1.0 (0.1.x beta since 2026-11-05, tested on 0.1.0); commit `uv.lock`, raise `<0.1` caps before `uv lock --upgrade-package zensical`, rebuild `--clean`, and keep CI cache-free.
- **Respect site branding**: the starter uses `~/.agents/DESIGN.md` light tokens and Google Sans; preserve existing or customer branding, and use [fmind-visuals](../fmind-visuals/SKILL.md) for Fmind logos/assets.

## Documentation

- [Get started](https://zensical.org/docs/get-started/) · [Create a site](https://zensical.org/docs/create-your-site/) · [Configuration](https://zensical.org/docs/setup/basics/) · [Authoring](https://zensical.org/docs/authoring/markdown/)
- [Validation](https://zensical.org/docs/setup/validation/) · [Plugins](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Customization](https://zensical.org/docs/customization/) · [Publishing](https://zensical.org/docs/publish-your-site/)
- Source: [zensical/zensical](https://github.com/zensical/zensical) · [zensical/docs](https://github.com/zensical/docs) · Releases: [Zensical](https://github.com/zensical/zensical/releases)
- Official skills: none upstream in `zensical/zensical` or `zensical/docs` (checked 2026-10-31). [Zensical Studio](https://zensical.org/studio) (VS Code) adds a preview, formatter, linter, and link refactoring for Zensical and MkDocs projects.
