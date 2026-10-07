---
name: fact-check
description: "Fact-check articles and posts: claims, lychee link checks, primary sources."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/fact-check
  created: "2026-10-04"
  updated: "2026-10-07"
---

# Fact-Check

Verify every material claim and link in a draft article, post, talk, or README section, and add primary sources where a claim needs one. Report findings with narrowed wording that would be true today; rewrite only when asked. [technical-publishing](../technical-publishing/SKILL.md) owns the publication pipeline, and a publishing project's local review skill (for example `review-content`) takes precedence for its own packages.

## Workflow

1. **Scope the source**: read the whole file and the author's raw notes when they exist; record the revision checked (`git log -1 --format=%h -- <file>` plus `git status --short <file>`). Published copy is immutable: report findings for an erratum instead of editing it.
1. **Build the claim ledger**: one row per material assertion: versions, defaults, numbers, dates, comparisons, quotations, attributions, availability ("open source", "GA", "free"), and personal results. Skip opinions, but check the facts an opinion rests on.

   | # | Claim (exact quote) | Kind | Support | Verdict | Fix |
   | - | ------------------- | ---- | ------- | ------- | --- |

1. **Verify, do not recognize**: confirm each row against a primary source opened in this session: the vendor's documentation or changelog, the repository, the lockfile or installed version, the paper, the official announcement. Prefer the canonical page over an aggregator, blog summary, or model memory. Personal facts trace only to the author's notes or explicit input; never supply them.
1. **Check links**: run lychee on the file, then open each cited page and confirm it says what the sentence claims; a resolving link that does not support its claim is the worse failure. A bare `--include-fragments` checks `#anchor` fragments only; use `--include-fragments=full` when the draft cites text fragments (`#:~:text=`).

   ```bash
   lychee --no-progress --include-fragments --max-retries 2 --format detailed <file>
   ```

1. **Add sources**: for an unsupported but true claim, propose the primary link at the claim, not a generic homepage; keep the existing link style (inline, reference, footnote). For an outdated or inflated claim, propose the smaller true form. Never invent a URL; name the missing source instead.
1. **Report**: verdict counts first (`supported`, `outdated`, `unsupported`, `wrong`, `broken link`), then the ledger rows that need action, ranked by reader impact. Include the date checked: versions, prices, and availability drift.

## Gotchas

- **Watch for quiet failures**: an intention in notes promoted to a present-tense fact, a number found in no source, a pin true when drafted but drifted since, someone else's result stated as the author's, and a "we" that claims a team that does not exist.
- **Verify comparison conditions**: check the baseline, equivalent task, outcome quality, and measurement limits; a token or time reduction alone does not prove productivity or cost.
- **Link checkers lie both ways**: bot-blocking sites return 403 or 429 to lychee yet work in a browser, and soft-404 pages return 200. Confirm suspicious results by opening the page; report login walls as unverifiable.
- **Treat remembered facts as hypotheses**: a fact you remember is a hypothesis; a fact you opened today is evidence. Say "unverified" rather than guessing.

## Documentation

- [lychee](https://lychee.cli.rs/) · [releases](https://github.com/lycheeverse/lychee/releases)
- Companion skills: [technical-publishing](../technical-publishing/SKILL.md) (publication), [repository-docs](../repository-docs/SKILL.md) (README and docs accuracy).
