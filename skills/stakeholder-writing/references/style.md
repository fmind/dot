# Style for Busy Readers

Defaults for formal documents and external readers; adapt when the reader or destination calls for it.

## Plain, literal language

Write active sentences with everyday words, one idea per short paragraph, and acronyms expanded at first use.

Before: `Batch → spot VMs ≈ -60% compute (preemptible, w/ retries); SLA risk ↑.`

After:

> Running nightly batch jobs on spot virtual machines cuts compute cost by about 60%. Google can reclaim these machines at short notice, delaying retried jobs by minutes rather than failing them. The main risk is missing the 7:00 report deadline if many machines are reclaimed at once.

## Code formatting

Use backticks only for commands, paths, or literal values the reader must copy — never for product names, concepts, or non-technical readers ("the invoice export writes to the EU bucket for 30 days", not `` `invoice_export` writes to `exports-eu` with `retention_days=30` ``).

## Terms and metrics

Define 1–2 essential terms inline. In formal documents, move other unfamiliar terms, units, and metrics to a **Key terms** annex (one line each), skipping daily team vocabulary. State meaning, unit, better direction (`**p95 latency**: time within which 95% of requests finish, in seconds; lower is better`), and baseline (`fell from 1.2 s to 0.4 s over 10,000 requests in the week of 6 October`).

## Numbers

- **Full context & locale**: include unit, currency, period, region, price date ("€4,200/month at October 2026 list prices in europe-west1"), and reader locale ("4 200 €" + decimal comma in French).
- **Precision & ranges**: round to input precision ("about €4,000 to €5,000/month", not "€4,213.57") and show conservative ranges naming the driving input.
- **Deltas & baselines**: separate percent from percentage points ("fell from 4% to 3%: 1 percentage point, a 25% reduction") against a named baseline.

## Titles, headings, and section summaries

Keep titles and headings short and literal ("Context", "Options", "Security", "Next steps"). Put the conclusion in the section's bold first sentence, never in the heading (slide decks use assertion-evidence titles per [slides.md](slides.md)).

| Element        | Before                                                                  | After                                                                                 |
| -------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Title          | Spot machines cut batch costs by 60%, with a small risk of late reports | Moving batch jobs to spot machines                                                    |
| Heading        | Moving the jobs keeps all data in the EU but adds two service accounts  | Security                                                                              |
| First sentence | We reviewed the security of the move.                                   | **Moving the jobs keeps all data in the EU but adds two service accounts to manage.** |

When top metadata helps, list `Type`, `Status` (Draft/Final), `Audience`, `Author`, and `Date` (one per line). Close long multi-finding sections with a 1–3 sentence `**Take-home messages**: ...` box.

## Examples, tables, and visuals

- **Concrete comparisons**: ground abstract claims with examples and compare options/periods in tables (shared criteria in columns, user labels preserved, recommended row marked).
- **Worded statuses**: pair color with words (`Low`/`Medium`/`High` or `Met`/`Partial`/`Not met` via CSS badges in HTML and 🟢 🟡 🔴 in Markdown/chat; keep badges out of prose).
- **Figures & citations**: draw SVG, Mermaid, or matplotlib visuals when faster than prose ([diagrams-as-code](../../diagrams-as-code/SKILL.md)), with conclusion captions and text/table alternatives. Cite source, link, and date on third-party figures (redraw or get permission for public docs).
- **Bold skim**: bold the take-home message, each section's opening sentence, and at most one phrase per paragraph so bold text alone carries the argument.

## Links and sensitivity

Link primary docs and standards inline, using plain `{link to ...}` placeholders when internal URLs are missing:

- **Reader access & URL leaks**: skip login-walled or dead links; describe locked sources in prose when hostnames, customer/person names, or ticket slugs in URLs leak context.
- **No tokens or session artifacts**: strip signed/expiring URLs, sharing grants, brain notes, local paths, agent/session links, and private repos.

## Destination and platform features

Apply `~/.agents/DESIGN.md` (Fmind Theme) or customer branding (≥16 px screen / ≥10 pt print body type, print-safe layout) using native primitives:

- **Standalone HTML / Markdown**: [report.html](../templates/report.html) (embedded WOFF2 fonts + data-URI images) or [report.md](../templates/report.md).
- **Zensical / GitHub**: admonitions/alerts, Mermaid fences, collapsible annexes, and tabs/task lists ([authoring](../../documentation-site/references/authoring.md)).
- **Google Docs**: [draft-doc](../../draft-doc/SKILL.md#format-choice) and [native `.md` dialect rules](../../draft-doc/SKILL.md#native-md-dialect-rules).
- **Email and chat**: short paragraphs, no headings or external images, and at most one short list.

## Honest framing

- **Evidence & neutrality**: ground confidence in named evidence, state unchecked gaps and flip conditions, compare options on equal criteria (including counter-evidence), and drop unsupported superlatives ("seamless", "guaranteed").
