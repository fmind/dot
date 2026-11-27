---
name: likec4
description: "Author opt-in LikeC4 C4 architecture models, validate in CI, and build interactive static explorers."
---

# LikeC4 Architecture Models (Opt-In)

Use LikeC4 for multi-container or multi-service systems that benefit from one validated C4 model (`architecture/*.c4`) with interactive `Context → Container → Component` drill-down. For single-service CLIs and libraries, stay on [d2](d2.md) `layers:` to avoid adding Node.js to the repo.

## Workflow

1. **Pin per project (opt-in)**: pin `node` and `"npm:likec4"` in the adopting repo's `mise.toml` (re-lock with `mise lock`; never force Node into minimal starters) and keep sources under `architecture/`.
1. **Model once, project views**: define `specification` element kinds (`actor`, `system`, `container`, `component`, `datastore`, `external`), declare the shared `model` (systems, containers, typed relationships with protocols), and expose focused `views` (`index` Context view plus scoped `of <system>` Container/Component views).
1. **Format (`format:c4`) & validate (`check:c4`)**:
   ```bash
   likec4 format architecture
   likec4 validate --max-warnings 0 architecture
   ```
   Wire `likec4 format architecture` under `format` and read-only `likec4 validate --max-warnings 0 architecture` as `check:c4` in `check:local` (checks syntax, semantics, and layout drift without a browser).
1. **Preview locally & build static portal**:
   ```bash
   likec4 start --listen 127.0.0.1 architecture
   likec4 build --base /<slug>/architecture/ --use-hash-history --output-single-file -o site/architecture architecture
   ```
   Mount `site/architecture` after `zensical build --clean --strict` per [mounted portals](../../docs/references/site/references/configuration.md#mounted-portals) so GitHub Pages serves the interactive explorer alongside project docs.
1. **Export text graphs without Playwright**: use `likec4 gen d2 --outdir ...`, `likec4 gen mermaid --outdir ...`, or `likec4 export json` when you need portable diagrams or machine-readable diffs in CI.

## Gotchas

- **Avoid `likec4 export png`/`jpg` in CI**: image export requires a headless Chromium/Playwright runtime; prefer `--output-single-file` static HTML builds or `likec4 gen d2`/`mermaid` in CI, and inspect locally when raster images are needed.
- **Bind dev server to loopback**: pass `--listen 127.0.0.1` to `likec4 start` so local previews never bind all interfaces.
- **Keep `--use-hash-history` on static hosts**: GitHub Pages has no SPA fallback route; hash history (`/#/view/...`) prevents 404s on deep links and refreshes.
- **Prevent model drift**: update `architecture/*.c4` in the same change/PR as any new container, datastore, or external dependency (pair with [openspec](../../openspec/SKILL.md) `archive` guidance and `fmind-review-architecture`).
- **Keep component diagrams grounded**: use LikeC4 for Context/Container boundaries and opt-in `tach` ([python/hardening](../../python/references/foundation/references/hardening.md)) for enforced Python module graphs instead of hand-drawing fine-grained code boxes.

## Documentation

- [LikeC4 docs](https://likec4.dev/) · [CLI reference](https://likec4.dev/tooling/cli/) · [likec4/likec4](https://github.com/likec4/likec4) ([releases](https://github.com/likec4/likec4/releases))
- Companion guides: [d2](d2.md) (single-service C4 `layers:`), [docs/site](../../docs/references/site/GUIDE.md) (mounting into Zensical), [openspec](../../openspec/SKILL.md).
