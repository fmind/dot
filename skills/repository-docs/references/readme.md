# README Standard

Answer three questions fast: **Is this for me? What will I get? How do I try it?**

## Workflow

1. **Inspect**: check manifests, entry points, supported platforms, install paths, and public anchors; separate shipped behavior from roadmap.
1. **Structure the journey** (adapt [README starter](../templates/README.md); use [README assets](readme-assets.md) for logos, illustrations, and badges):
   - **Opening**: SVG logo, name, 1-sentence purpose, verified badges, short nav (**Try it** + 3–4 links), hero illustration (Typst 2× PNG + `.typ` or SVG).
   - **Result & Quickstart** (mergeable for small CLIs/libs): real input → output example, prerequisites → single recommended install → minimal config → first command → observed output (keep contributor setup separate).
   - **Why / How it works / Fit & limits / Next steps**: 3–5 concrete benefits, brief mechanism + diagram or layout, honest platform/cost/data limits, and task-oriented doc links.
1. **Verify**: execute the install and quickstart in a clean environment with synthetic data, then check light/dark rendering at desktop and mobile widths and confirm every badge/link resolves.

## Reference patterns

Reviewed 2026-09-26 as inspiration, not verbatim templates:

- [Brain Framework](https://github.com/fmind/brain-framework): custom SVG logo, concept diagrams, owned-file benefits, explicit fit/limits (pull first result earlier and link deep reference docs).
- [OpenClaw](https://github.com/openclaw/openclaw/blob/main/README.md): direct purpose, clear onboarding, goal-oriented doc routes.
- [Hermes Agent](https://github.com/NousResearch/hermes-agent/blob/main/README.md): sharp differentiator and concrete usage examples.
- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) · [workflow badges](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge) · [theme-aware pictures](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github)
