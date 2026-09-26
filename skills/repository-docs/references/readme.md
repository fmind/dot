# README Standard

Help a new reader answer three questions: **Is this for me? What will I get? How do I try it?** Treat the README as the project's front door. Keep it useful without requiring the reader to understand the architecture first.

## Workflow

1. **Inspect before writing**: read project rules, the existing README, entry points, manifests, supported platforms, installation paths, examples, and docs. Preserve the author's voice, established identity, and public anchors. Separate current behavior from plans.
1. **Choose one reader and one outcome**: identify the primary audience, the task they struggle with, and the result the project delivers. Use concrete verbs and nouns; let a short tagline add personality after the purpose is clear.
1. **Build the reader journey** below; adapt the [starter](../templates/README.md) for a new project. Omit irrelevant sections. Default to a few minutes of reading, with detailed manuals behind links; word counts are an editing aid, not a gate.
1. **Verify the first result**: run the recommended installation and smallest useful workflow in a disposable environment, using synthetic data. Record actual output or capture the actual UI; state external prerequisites and anything not exercised.
1. **Review the rendered page** using the acceptance checks below. Report remaining gaps without claiming publication, hosted CI, or adoption from local checks.

## Reader journey

| Order             | Content                                                                               | Reader's question                                  |
| ----------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Opening           | Compact SVG logo, project name, one-sentence purpose, useful badges, short navigation | What is this, who is it for, and where do I start? |
| Result            | One real input → output example, screenshot, or short demo with a text equivalent     | What useful thing will happen?                     |
| Quickstart        | Prerequisites → install → necessary configuration → first use → expected result       | Can I make that happen myself?                     |
| Why this project? | Three to five distinct benefits, each tied to observable behavior                     | Why would I choose it?                             |
| How it works      | A short explanation, small diagram, or file layout only when it clarifies use         | What do I need to understand?                      |
| Fit and limits    | Relevant trade-offs, maturity, supported platforms, cost and data boundaries          | Does it suit my situation?                         |
| Next steps        | Task-oriented docs, support, contribution and license links                           | Where do I go next?                                |

The result and quickstart may be one section for a small CLI or library. A short explanation can come first if essential to safe use; avoid a terminology lesson before the reader sees value. Use one obvious primary action such as **Try it**, with three or four secondary links. Keep ordinary body text left-aligned and headings descriptive. GitHub already provides an outline; add a manual table of contents only when it helps.

## Visual identity

- **Default to a project-owned SVG logo** in a stable asset path such as `docs/assets/logo.svg`. Reuse an established mark; new marks should be simple and recognizable at small sizes. Keep editable vector sources, a `viewBox`, and explicit display dimensions; around 96–128 pixels is a starting point for a standalone mark, not a fixed rule for wordmarks.
- **Make it portable**: use self-contained SVG paths/shapes with no scripts, remote resources, or required installed fonts. Outline lettering when needed. Include meaningful image alt text and keep the name and purpose as real text outside the image. SVG syntax validation does not replace visual inspection.
- **Check light and dark themes**: prefer one mark that works on both, or use GitHub's supported `picture` pattern with a fallback. Verify at narrow/mobile and desktop widths without tiny text or horizontal scrolling. A large banner must earn its space by explaining the product.
- **Respect identity**: for Fmind projects use [fmind-visuals](../../fmind-visuals/SKILL.md) and the canonical theme unless the project specifies otherwise. Retain a distinct project symbol; do not reuse another project's mascot. GitHub controls README text fonts; apply brand typography to owned assets and sites.
- **Show the product**: use a real screenshot for a UI, a short captured terminal session or input/output block for a CLI, and a runnable snippet with its result for a library. Use synthetic data, readable type, a static/text fallback for motion, and a small asset payload. Do not fabricate screenshots, results, users, or testimonials.

Use relative repository assets by default so branches and local previews stay coherent. When package registries or documentation exports require absolute URLs, verify their renderer and asset availability; do not point an unreleased README at an asset that exists only locally.

## Badges with evidence

Use one compact row, usually three or four badges. Each badge answers a decision question, has descriptive alt text, and links to the underlying evidence. Keep styles consistent.

| Badge           | Include when                                               | Link to                                   |
| --------------- | ---------------------------------------------------------- | ----------------------------------------- |
| CI              | The named workflow exists; scope it to the intended branch | That workflow's runs                      |
| Release/package | A release or package actually exists                       | Releases or the package registry          |
| Compatibility   | Supported runtimes/platforms are declared and checked      | Package metadata or support documentation |
| License         | The license has been chosen and is present                 | The actual license file                   |

Coverage, docs builds, downloads, and other badges are optional when they add useful evidence. CI green is not a security certification or proof of production readiness. Omit novelty badges, duplicate signals, unverified claims, and popularity widgets that crowd out the first useful action. Never invent counts or imply adoption from stars.

Private repositories remain private. Prefer local assets and authenticated GitHub links; omit third-party badges that require private metadata or tokens. Do not create public resources merely to make a badge work. Before a first release, use honest development status and the verified source-install route; add release badges after publication.

## First successful use and trust

- Show one recommended install path, a short copyable command block, and a recognizable success result. Link alternate platforms and advanced installs. State prerequisites, accounts, credentials, network access, and paid services before the step that requires them; document variable names and storage without real secrets.
- Prefer the supported package manager; an installer script is not a requirement for approachability. Keep user installation separate from cloning/building for contribution. Match version pins to the project's release policy and update them with the example.
- Pair benefits with mechanisms or examples: explain what a user can accomplish and what makes that possible. Quantitative claims need reproducible evidence, version/date, sample size, and relevant limits; do not add a benchmark section without measurements. Avoid unsupported superlatives and promises of automatic learning.
- Separate shipped integrations, reviewed examples, and extensions users must write. Say where data lives and what can leave the machine when relevant. Put consequential permissions or execution warnings next to the affected action, with deeper security details behind a link.
- Keep architecture catalogs, full command tables, release procedures, and agent rules in their canonical docs. Use a compact goal → guide table only if several routes need explanation. Link a real issue/support channel and contributor guide; a new chat community is not a prerequisite.
- Align the repository description, relevant topics, homepage, package description, and documentation landing page with the same purpose. Prepare these when scaffolding; remote changes follow existing authorization. A social preview is optional and uses the same identity.

## Acceptance review

1. **Opening**: the name, intended reader, concrete outcome, and next action are clear without scrolling through a feature inventory. The logo supports recognition and does not dominate the page.
1. **First use**: the documented happy path works from its declared prerequisites and produces the shown result. A demo or expected output makes success recognizable; untested external steps are explicit.
1. **Evidence**: badges resolve to the correct repository, workflow, branch, package, and license. Claims distinguish current behavior, examples, plans, and measured results.
1. **Rendering**: inspect the rendered Markdown, SVG, images, and code blocks in light/dark themes at desktop and narrow widths. Check useful alt text, readable contrast, and asset payloads. When republishing to a registry or docs site, check that surface too.
1. **Maintenance**: run relevant formatting, relative-link/anchor checks, and documentation builds; check external destinations within access boundaries. Preserve established anchors or provide deliberate migration links. No unresolved placeholders or unavailable destinations remain.

This is an editorial standard, not evidence that a README increases adoption. Measure actual onboarding outcomes when available: successful first runs, time to first useful result, and recurring setup questions, with denominators and observation periods.

## Reference patterns

Reviewed on 2026-09-26; these are evolving examples, not templates to copy verbatim or evidence of product quality.

- [Brain Framework](https://github.com/fmind/brain-framework): the local reference demonstrates a distinctive SVG, useful badges, owned-file benefits, and explicit fit/limits. Keep those strengths; make the first result earlier and move detailed reference material behind links.
- [OpenClaw](https://github.com/openclaw/openclaw/blob/main/README.md): borrow the direct purpose, visible install/onboarding path, and goal-oriented documentation routes.
- [Hermes Agent](https://github.com/NousResearch/hermes-agent/blob/main/README.md): borrow the memorable differentiator and concrete usage descriptions; validate comparative claims independently and keep operational detail out of the opening.
- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), [workflow badges](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge), and [theme-aware pictures](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github).
