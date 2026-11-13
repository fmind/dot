# Human Style & Visual Primitives

Curate insight, write plainly, and use every visual primitive the destination supports.

## Kill AI Dumps (Before → After)

### Example 1 — Status update or Slack/email

**Before (AI dump: backticks, jargon, raw internals):**

> `ingest_worker` in `europe-west1` hit OOMKilled on `BatchJob-v2` due to `polars.collect()` spikes (`RSS=14.2GiB`); switched to `LazyFrame.sink_parquet()` -> latency `-42%` / cost `-35%` -> PR #142 merged (`Status: Ready`).

**After (Humanized: curated signal, plain words, scannable highlight):**

> **Nightly imports are stable and 35% cheaper.** Switching to streaming writes stopped memory crashes in Europe and cut job duration by ~40% (18 min to 10 min across 50k daily files).
>
> **🟢 Ready for release** — No action needed unless you want to backfill last week's failed batch by Friday.

### Example 2 — Code prose & backtick discipline

Reserve backticks solely for exact CLI commands or file paths a technical reader will run or open. Never backtick product names, regions, configs, metrics, or status words (`europe-west1`, `Recommended`, `retention_days=30`, `v16.1.0`).

## Visual Formatting Matrix by Medium

Never ship flat plain text when the medium supports visual structure:

| Medium                          | Highlight & emphasis                                        | Separation & grouping                                             | Visual blocks & illustrations                                             |
| ------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **HTML / PDF**                  | `<mark>` / `.hl` amber highlight pill                       | Top brand band, `<hr>` dividers, `.summary` / `.ask` left-borders | KPI `.tiles`, `.badge` pills, Typst / SVG charts                          |
| **GitHub / Zensical MD**        | `> [!IMPORTANT]` / `> [!TIP]` / `> [!WARNING]`              | `---` horizontal rules, `<details>` for depth                     | Bold-first 3-col tables, `🟢`/`🟡`/`🔴` worded pills, Mermaid / Typst PNG |
| **Google Docs (`.md`)**         | `> **Key signal:** ...` left-border quote                   | Spaced `---` dividers, clear `##` hierarchy                       | GFM comparison tables + **Typst 2× PNG cards**                            |
| **Google Docs (`.gdoc`)**       | Native text highlights & brand accent                       | Section dividers, shaded table header/recommended rows            | Native tables + 2× Typst figures in `assets/`                             |
| **Gmail (`draft-mail`)**        | `<strong>` on 1–2 signals; optional left-border callout div | Short 1–2 sentence `<p>` blocks with air between paragraphs       | ≤4 scannable bullets (bold lead-in per item)                              |
| **Slides (`draft-typst-deck`)** | `#hl[...]` highlight box + `#callout`                       | Clean `#FFFFFF` canvas, 1 focal visual per slide                  | KPI strip, `split-cards`, `bar-row`, `step-flow`                          |
| **Chat / Slack**                | Bold `*takeaway*`, `>` blockquote                           | Blank lines between signal, impact, and ask                       | Compact inline status pill (`🟢 Ready`, `🔴 Blocked`)                     |

## Structure, Numbers, & Evidence

- **Assertion-first paragraphs**: open every section with a bold conclusion sentence; keep headings short and literal (`Context`, `Options`, `Next steps`), except slide titles which carry the takeaway ([slides.md](slides.md)).
- **Bold skim test**: reading only bold text + callouts should convey the full recommendation and ask.
- **Numbers with context**: round to decision precision (`~€4,000–€5,000/month`, not `€4,213.57`), state unit, period, locale (`4 200 €` + decimal comma in French), and baseline (`fell from 4% to 3%: 1 percentage point, a 25% drop`).
- **Balanced framing & leaks**: show equal criteria across options (including doing nothing), state flip conditions, use `"I"` for solo drafts, and never leak internal hostnames, signed URLs, or customer identifiers (use `{link to ...}` placeholders when URLs are missing).
