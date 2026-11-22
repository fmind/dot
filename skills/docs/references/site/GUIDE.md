---
name: site
description: "Build Zensical docs, courses, and API sites; deploy Pages or migrate MkDocs/Hugo."
---

# Documentation Sites

Use Zensical by default for docs, courses, and blogs; keep an existing generator only when required or requested. [docs/repository](../repository/GUIDE.md) owns README/AGENTS sync; [humanize](../../../humanize/SKILL.md) and [authoring](references/authoring.md) own prose and Zensical visual blocks.

## Workflow

1. **Inspect existing sites**: preserve content, URLs, and publishing rules; for MkDocs or Hugo sites, follow [migration](references/migration.md).
1. **Bootstrap locked**: check the [latest release](https://github.com/zensical/zensical/releases) and add Zensical to `dev` (run `zensical new` in scratch if `docs/` or `zensical.toml` exists, since it never overwrites):
   ```bash
   uv init --bare <slug> && cd <slug>
   UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev 'zensical>=0.1.1,<0.2' && uv run zensical new .
   ```
1. **Apply the starter**: copy [zensical.toml](templates/zensical.toml), [index.md](templates/index.md) (`docs/index.md`), `~/.agents/themes/zensical/fmind.css` (`docs/stylesheets/fmind.css`, or customer CSS), and [abbreviations.md](templates/abbreviations.md) (`includes/abbreviations.md`); delete `docs/markdown.md`, fill placeholders, set `site_url`, prune unused sections, and check [configuration](references/configuration.md).
1. **Write under `docs/`**: follow [humanize](../../../humanize/SKILL.md) and [authoring](references/authoring.md); start courses from [lesson.md](templates/lesson.md) with local exercises and [VHS](../../../diagrams-as-code/references/recording/GUIDE.md) demos + static fallbacks.
1. **Wire tasks and ignores**: merge [mise.toml](templates/mise.toml) and shared config ([dprint.json](../../../mise/templates/dprint.json), [betterleaks.toml](../../../code-security/templates/betterleaks.toml), [lefthook](../../../github/references/lefthook.md), `.python-version`, [bootstrap](../../../github/references/bootstrap.md)); ignore `site/` and `.cache/`, format via [dprint](../../../mise/references/dprint.md), and test snippets via [python/foundation](../../../python/references/foundation/GUIDE.md).
1. **Validate & review adversarially**: require `uv run --locked zensical build --clean --strict` exit 0 (`No issues found`). Serve `uv run --locked zensical serve -a 127.0.0.1:${PORT:-8000}` and inspect desktop + `390x844` mobile screenshots (nav, search, light/dark, diagrams, keyboard, copy buttons via [playwright](../../../web-frontend/references/playwright.md) / [chrome-devtools](../../../web-frontend/references/chrome-devtools.md)), snippet tests, `vale`, `lychee`, and `fmind-review-docs` + `fmind-review-frontend` ([subagent](../../../subagent/SKILL.md)).
1. **Publish**: use pinned [docs.yml](templates/docs.yml) as `.github/workflows/docs.yml` (replaces `ci.yml` on standalone Pages repos since it runs `mise run all`); enabling Pages or deploying requires publication authority.

## Gotchas

- **Read errors from the top**: strict builds print `file:line:col` before tracebacks and emit ANSI even when piped (`perl -pe 's/\e\[[0-9;]*m//g'`).
- **Strict mode checks targets, not Markdown syntax**: unclosed fences and unknown icons build silently—inspect rendered pages.
- **Set `site_url` accurately** ([configuration](references/configuration.md)): `llmstxt` aborts without it and wrong prefixes break cards, sitemaps, and instant nav.
- **Pre-1.0 limits** ([native plugins](references/configuration.md#native-plugins)): `0.1.x` drops unsupported MkDocs Python plugins (`gen-files`, `hooks`) silently; `docs_dir` cannot be `.`, uv symlinks fail, and `serve` lacks `--strict`.
- **Keep site branding**: starter uses `~/.agents/DESIGN.md` tokens and Google Sans; preserve existing/customer branding and generate Fmind visuals via [diagrams-as-code](../../../diagrams-as-code/SKILL.md).

## Documentation

- [Get started](https://zensical.org/docs/get-started/) · [Configuration](https://zensical.org/docs/setup/basics/) · [Plugins](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Publishing](https://zensical.org/docs/publish-your-site/) · [zensical/zensical](https://github.com/zensical/zensical) ([releases](https://github.com/zensical/zensical/releases)) · [Zensical Studio](https://zensical.org/studio) (VS Code preview/lint).
