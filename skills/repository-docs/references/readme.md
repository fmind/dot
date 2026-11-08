# README Standard

Help a new reader answer three questions: **Is this for me? What will I get? How do I try it?** Treat the README as the project's front door. Keep it useful without requiring the reader to understand the architecture first.

## Workflow

1. **Inspect before writing**: read project rules, the existing README, entry points, manifests, supported platforms, installation paths, examples, and docs. Preserve the author's voice, established identity, and public anchors. Separate current behavior from plans.
1. **Build the reader journey** below; adapt the [starter](../templates/README.md) for a new project. Omit irrelevant sections. When creating or changing a logo, illustration, or badge, follow [README assets](readme-assets.md). Default to a few minutes of reading, with detailed manuals behind links; word counts are an editing aid, not a gate.
1. **Verify the first result**: run the recommended installation and smallest useful workflow in a disposable environment, using synthetic data. Record actual output or capture the actual UI; state external prerequisites and anything not exercised.
1. **Run the acceptance review**: inspect the rendered page in light and dark themes at desktop and narrow widths, and on any registry or docs site that republishes it; every badge and claim links to its evidence, and no placeholder or broken destination remains. Report remaining gaps without claiming publication, hosted CI, or adoption from local checks.

## Reader journey

| Order             | Content                                                                                                  | Reader's question                                  |
| ----------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Opening           | Compact SVG logo, project name, one-sentence purpose, useful badges, short navigation, hero illustration | What is this, who is it for, and where do I start? |
| Result            | One real input → output example, screenshot, or short demo with a text equivalent                        | What useful thing will happen?                     |
| Quickstart        | Prerequisites → install → necessary configuration → first use → expected result                          | Can I make that happen myself?                     |
| Why this project? | Three to five distinct benefits, each tied to observable behavior                                        | Why would I choose it?                             |
| How it works      | A short explanation beside an SVG illustration of the mechanism, or a file layout                        | What do I need to understand?                      |
| Fit and limits    | Relevant trade-offs, maturity, supported platforms, cost and data boundaries                             | Does it suit my situation?                         |
| Next steps        | Task-oriented docs, support, contribution and license links                                              | Where do I go next?                                |

The result and quickstart may be one section for a small CLI or library. A short explanation can come first if essential to safe use; avoid a terminology lesson before the reader sees value. Use one obvious primary action such as **Try it**, with three or four secondary links. Keep ordinary body text left-aligned and headings descriptive. GitHub already provides an outline; add a manual table of contents only when it helps. Show one recommended install path through the supported package manager (an installer script is optional), kept separate from contributor setup.

## Reference patterns

Reviewed on 2026-09-26; these are evolving examples, not templates to copy verbatim or evidence of product quality.

- [Brain Framework](https://github.com/fmind/brain-framework): the local reference demonstrates a distinctive SVG logo, concept illustrations (a loop hero, a before/after, a vocabulary mapping), useful badges, owned-file benefits, and explicit fit/limits. Keep those strengths; make the first result earlier and move detailed reference material behind links.
- [OpenClaw](https://github.com/openclaw/openclaw/blob/main/README.md): borrow the direct purpose, visible install/onboarding path, and goal-oriented documentation routes.
- [Hermes Agent](https://github.com/NousResearch/hermes-agent/blob/main/README.md): borrow the memorable differentiator and concrete usage descriptions; validate comparative claims independently and keep operational detail out of the opening.
- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), [workflow badges](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge), and [theme-aware pictures](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github).
