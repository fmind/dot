# Visual Primitives and Rewrites

Pick only primitives supported by the target renderer. Never paste raw HTML into Slack, GitHub alerts into Zensical, or raw Markdown tables into Gmail.

## Before and after

Before (executive incident memo wall):

> At 09:12 UTC `checkout-api` returned `502` for `eu-west1` (`pg_pool_max=20`, `read_replica_enabled=false`). Scaled instances `2`->`6`, set `pg_pool_max=60`, enabled replica at 09:27 UTC; 15 min impact (`~1.8%` failed checkouts).

After:

> **Resolved: European checkout errors lasted 15 minutes; database capacity is tripled before tonight's peak.**
>
> **Status:** Recovered · **Impact:** under 2% of European checkouts failed between 09:12 and 09:27 UTC.
>
> | Area                 | Previous limit      | Current headroom    | Follow-up            |
> | :------------------- | :------------------ | :------------------ | :------------------- |
> | Database connections | Saturated at 20     | **60 active slots** | Alert at 75% load    |
> | Read traffic         | Single primary node | **Replica enabled** | Add load test Friday |

## Channel primitives

Use `~/.agents/DESIGN.md` tokens (unless customer branding applies): ink `#202124`, accent `#174EA6`, neutral `#F1F3F4`, selection `#D2E3FC`, ok `#0D652D`/`#CEEAD6`, risk `#934900`/`#FEEFC3`, blocker `#A50E0E`/`#FAD2CF`.

| Channel                     | Guide                                                                                                                  | Supported primitives                                                                                                                     | Avoid                                                  |
| :-------------------------- | :--------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------- |
| **Gmail HTML**              | [draft/mail](../../draft/references/mail/GUIDE.md)                                                                     | Routine: `<p>`, `<strong>`, `<ul>`/`<ol>`, `<a href>`; executive briefs: 1 inline-styled accent callout or `<mark>` (never stacked)      | Newsletter chrome, `<style>`, `<script>`, raw Markdown |
| **Google Docs (`.gdoc`)**   | [draft/doc](../../draft/references/doc/GUIDE.md), [gdoc](../../draft/references/doc/references/gdoc.md)                | Inline-styled HTML (`<mark>`, 1x1 callout table, shaded rows, Base64 PNG) or `documents.batchUpdate`                                     | CSS Grid/Flexbox, `var(...)`, nested tables, `<style>` |
| **Google Docs (`.md`)**     | [dialect](../../draft/references/doc/references/dialect.md)                                                            | `---` rules, 3–4 col tables, bold lead-ins, blockquotes, `<=440pt` compiled PNGs                                                         | Raw HTML, `<details>`, `[!IMPORTANT]` alerts           |
| **GitHub**                  | [github](../../github/SKILL.md), [docs/repository](../../docs/references/repository/GUIDE.md)                          | `> [!IMPORTANT]` GFM alerts, status pills, compact tables, `<details>` for annexes                                                       | Zensical `!!!` blocks, raw `<style>`, link walls       |
| **Zensical**                | [docs/site](../../docs/references/site/GUIDE.md)                                                                       | `==mark==`, 4-space indented `!!! note` / `??? info` admonitions, `=== "Tab"`                                                            | GitHub `[!IMPORTANT]` syntax                           |
| **Jira / Confluence**       | [cloud-ops/acli](../../cloud-ops/references/acli.md)                                                                   | Native ADF panels (`info`/`warning`/`success`/`error`), lozenges, tables, expand macros                                                  | Raw Markdown syntax                                    |
| **Slides (Typst / Native)** | [draft/typst-deck](../../draft/references/typst-deck/GUIDE.md), [draft/slides](../../draft/references/slides/GUIDE.md) | 1 focal visual + micro-phrases (`~40–90`w live / `~60–110`w async; `1–3`w/cell matrices & `Annex · Sources` ok); nuance in speaker notes | Prose paragraphs, multi-chart slides, bullet walls     |
| **Sheets**                  | [draft/sheets](../../draft/references/sheets/GUIDE.md)                                                                 | Frozen bold header row, explicit currency/percent/date formats, right-aligned numbers, `RAW` inputs                                      | Mixed untrusted `USER_ENTERED` text                    |
| **Chat / Slack**            | [gws/chat](../../gws/references/chat.md)                                                                               | `<= 60–80`w (`3–5` lines): bold ask/outcome, 2–3 plain bullets, sources in thread reply                                                  | Headings, raw HTML, Markdown tables                    |
