# README Standard

Answer three questions fast: **Is this for me? What will I get? How do I try it?**

## Workflow

1. **Inspect**: check manifests, entry points, supported platforms, install paths, and public anchors; separate shipped behavior from roadmap.
1. **Structure the journey** (adapt [README starter](../templates/README.md)):
   - **Opening**: SVG logo, name, 1-sentence purpose, verified badges, short nav (**Try it** + 3–4 links), hero illustration (Typst 2x PNG + `.typ` or SVG).
   - **Result & Quickstart** (mergeable for small CLIs/libs): real input → output example, prerequisites → single recommended install → minimal config → first command → observed output (keep contributor setup separate).
   - **Why / How it works / Fit & limits / Next steps**: 3–5 concrete benefits, brief mechanism + diagram or layout, honest platform/cost/data limits, task-oriented doc links, and explicit `LICENSE` + security policy (`SECURITY.md` or inherited `/security/policy`) links on public repos.
1. **Verify**: execute the install and quickstart in a clean environment with synthetic data, then check light/dark rendering at desktop and mobile widths and confirm every badge and link resolves.

## Visual Identity & Badges

- **Self-contained SVG logo** (`docs/assets/logo.svg`, ~96–128 px mark with `viewBox` and explicit dimensions): pure vector paths/shapes, outlined lettering, no scripts, remote loads, or system-font dependencies; keep project name/purpose as real text outside the image.
- **Theme & viewport**: support light and dark GitHub themes (single mark or `<picture>` fallback) and mobile/desktop widths without tiny text or horizontal scroll.
- **Concept illustrations**: hero diagram below the opening plus 1 visual per core mechanism via [Typst](../../../../diagrams-as-code/references/typst.md) (`docs/assets/<concept>.png` at 2x `192 PPI` with `<concept>.typ` committed beside it; optional `.svg`) or the [SVG guide](../../../../diagrams-as-code/references/svg/GUIDE.md) (opaque light card, full text equivalent, link to full-size asset); use [D2](../../../../diagrams-as-code/references/d2.md) for routed architecture graphs and reserve [Mermaid](../../../../diagrams-as-code/references/mermaid.md) for inline contributor/reference docs.
- **Brand & URLs**: follow customer branding or [diagrams-as-code](../../../../diagrams-as-code/SKILL.md) + `~/.agents/DESIGN.md`; use relative paths by default (verify absolute URLs when publishing to PyPI/docs sites, and never link local-only assets from a published README).
- **Badges with evidence**: use one row of 3–4 consistent badges with alt text and evidence links: **CI** (branch-scoped workflow runs), **Release/package** (once published), **Compatibility** (checked runtime metadata), and **License** (`LICENSE`). Omit novelty/vanity badges, unverified claims, and third-party badges on private repos.

## Documentation

- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) · [workflow badges](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge) · [theme-aware pictures](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github) · [humanize](../../../../humanize/SKILL.md)
