# README Assets

Create or update README logos, illustrations, and badges ([README guidance](readme.md) owns page flow).

## Visual identity

- **Self-contained SVG logo** (`docs/assets/logo.svg`, ~96–128 px mark with `viewBox` and explicit dimensions): pure vector paths/shapes, outlined lettering, no scripts, remote loads, or system-font dependencies; keep project name/purpose as real text outside the image.
- **Theme & viewport**: support light and dark GitHub themes (single mark or `<picture>` fallback) and mobile/desktop widths without tiny text or horizontal scroll.
- **Concept illustrations**: hero diagram below the opening plus 1 visual per core mechanism via [Typst](../../diagrams-as-code/references/typst.md) (`docs/assets/<concept>.png` at 2× `192 PPI` with `<concept>.typ` committed beside it; optional `.svg`) or the [SVG guide](../../diagrams-as-code/references/svg/GUIDE.md) (opaque light card, full text equivalent, link to full-size asset); use [D2](../../diagrams-as-code/references/d2.md) for routed architecture graphs and reserve [Mermaid](../../diagrams-as-code/references/mermaid.md) for inline contributor/reference docs.
- **Brand & URLs**: follow customer branding or [diagrams-as-code](../../diagrams-as-code/SKILL.md) + `~/.agents/DESIGN.md`; use relative paths by default (verify absolute URLs when publishing to PyPI/docs sites, and never link local-only assets from a published README).

## Badges with evidence

Use one row of 3–4 consistent badges, each with alt text and an evidence link: **CI** (branch-scoped workflow runs), **Release/package** (only once published), **Compatibility** (checked runtime metadata), and **License** (`LICENSE`). Omit novelty/vanity badges, unverified claims, and third-party badges on private repos.
