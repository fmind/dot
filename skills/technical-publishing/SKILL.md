---
name: technical-publishing
description: "Prepare and publish technical articles: canonical site and channel copy."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/technical-publishing
  created: "2026-08-30"
  updated: "2026-10-04"
---

# Publish Technical Articles

Publish technical articles from package sources through review, canonical web publication, and channel copy. Third-party documentation sites and static websites use project-local documentation tooling, while software releases use [release](../git-delivery/references/release/GUIDE.md). Run the project-owned CLI from the publishing checkout:

```bash
mise run pub -- init article <slug>                       # scaffold directories and draft
mise run pub -- check <package> --publish-ready            # offline readiness gate
mise run pub -- publish <package> --site <site-directory> --dry-run # preview publication
```

## Workflow

1. **Read the project contract first**: inspect its `AGENTS.md`, current CLI help, and local publishing skill for the requested deliverable. The [package overview](references/packages.md) is orientation, not a replacement for the current schema or publication policy.
1. **Package pipeline**: prepare and review the article and channel deliverables inside the package before publication; `draft.txt` contains raw notes that agents never edit; see [Package layout](references/packages.md).
1. **Voice and boundaries**: adhere to the editorial voice in [Voice and identity](references/voice.md); agree the register before drafting; never invent anecdotes, clients, or metrics; cut hype, decorative lists, and empty corporate summaries.
1. **Visuals**: explanatory diagrams follow [fmind-visuals](../fmind-visuals/SKILL.md) and [d2](../diagrams-as-code/references/d2.md) using the light-surface theme; store `.d2` sources beside rendered PNGs.
1. **Terminal demos**: use the shared [VHS workflow](../fmind-visuals/references/recording.md), retain the tape and synthetic inputs beside the export, and provide a transcript or static alternative; recording does not publish the asset.
1. **Fact-check**: verify claims and links with [fact-check](../fact-check/SKILL.md) before review and after late edits.
1. **Canonical publication**: publish only when authorized for the package, following the project's publishing skill before omitting `--dry-run`: the command exports, opens and merges a site PR, verifies the live article, records publication, and retires the temporary `article.md`. Prepare corrections through the site's explicit erratum or edition workflow; ownership does not authorize rewriting published text.
1. **Channel copy**: use the session's channel selection, otherwise the project's defaults: article SEO, LinkedIn, and X. Prepare selected adaptations in `posts/`; Medium imports the live canonical URL and needs no duplicate `medium.md`. Channels are posted by hand, never automated or scheduled. When the project has no post workflow of its own, write and check the copy for article and announcement packages with [social-post](../social-post/SKILL.md); this skill keeps the package, channel selection, and publication log.

## Documentation

- [Package layout](references/packages.md) · [Voice and identity](references/voice.md)
- Companion skills: [fact-check](../fact-check/SKILL.md) (claims and links), [social-post](../social-post/SKILL.md) (channel copy), [fmind-visuals](../fmind-visuals/SKILL.md) (diagram theme and brand), [d2](../diagrams-as-code/references/d2.md) (diagram source), and [release](../git-delivery/references/release/GUIDE.md) (software releases).
