# Style for Busy Readers

Defaults for documents read outside the session; adapt them when the reader or the destination calls for it. Where a guideline is easy to misread, a before and after example follows it.

## Plain, literal language

Write complete sentences with a subject and a verb, everyday words, and the active voice, and keep one idea per short paragraph. Replace arrows, slash chains, stacked parentheses, and coined labels with sentences, and expand each acronym at first use.

Before:

> Batch → spot VMs ≈ -60% compute (preemptible, w/ retries); SLA risk ↑.

After:

> Running the nightly batch jobs on spot virtual machines would cut their compute cost by about 60%. Google can reclaim these machines at short notice in exchange for the lower price. The jobs already retry automatically, so a reclaimed machine delays a job by minutes rather than failing it. The main risk is missing the 7:00 report deadline when many machines are reclaimed at once.

## Terms and metrics

Put the terms, units, and metrics this reader may not know in a **Key terms** block right after the executive summary, one line each, and skip those they use daily, such as CVE for a security team. For a metric, give what it measures, its unit, and which direction is better, and its baseline where you use it. A short email or chat message defines its one or two terms inline instead.

Before:

> p95 dropped to 400 ms.

After, with this line in Key terms:

> **p95 latency**: the time within which 95% of requests finish, in seconds; lower is better.

And this sentence in the body:

> The p95 latency fell from 1.2 s to 0.4 s after the change. We measured it over 10,000 requests in the week of 6 October.

## Numbers

- **Give every figure its context**: unit, currency, period, region, and price date, such as "€4,200 per month at October 2026 list prices in the europe-west1 region".
- **Round to what the inputs support**: "about €4,000 to €5,000 per month", not "€4,213.57".
- **Show conservative ranges for estimates**: name the input that drives the range and show the result at both ends.
- **Separate percent from percentage points**: "the error rate fell from 4% to 3%, one percentage point or a 25% reduction".
- **Compare with a baseline**: "30% cheaper than today's spend on the managed service, at today's volume".
- **Follow the reader's conventions**: in French, write "4 200 €" and use a decimal comma.

## Titles, headings, and section summaries

Titles and headings are short names for navigation; the conclusion goes in the bold first sentence of the section, where it has room to be precise.

| Element        | Before                                                                  | After                                                                                 |
| -------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Title          | Spot machines cut batch costs by 60%, with a small risk of late reports | Moving batch jobs to spot machines                                                    |
| Heading        | Moving the jobs keeps all data in the EU but adds two service accounts  | Security                                                                              |
| First sentence | We reviewed the security of the move.                                   | **Moving the jobs keeps all data in the EU but adds two service accounts to manage.** |

Put the metadata at the top, one field per line: type, status (draft or final), audience, author, and date.

> Type: Decision memo\
> Status: Draft\
> Audience: Engineering and product leads\
> Author: {name}\
> Date: 26 October 2026

Close a section that runs past a few paragraphs or mixes several findings with a "Take-home messages" box of one to three sentences; short sections need none.

> **Take-home messages**: from December, the two models cost the same per token, so the pilot's measure of tokens per task decides the cheaper option.

## Examples, tables, and visuals

- **Make abstract claims concrete**: "for example, the invoice job that runs at 2:00 and takes 40 minutes".
- **Use a table for comparisons**: options or periods in rows, the same criteria in columns, numbered options, and the recommended row marked.
- **Flag ratings with a color and a word**: Low, Medium, High for risk, or Met, Partial, Not met for requirements, in green, amber, and red. Use the template's badges in HTML, because emoji depend on the reader's fonts, and 🟢 🟡 🔴 in Markdown and chat; never rely on color alone, and keep status marks out of running prose.
- **Prefer a figure to a paragraph of numbers**: a chart for numbers and trends (inline SVG or matplotlib, following the host's data-visualization skill when it has one) and a diagram for a flow, an architecture, or a timeline. Give each a caption that states its conclusion and a table or text alternative.
- **Quote third-party figures as a person would**: in a private document for a client team or a small circle, embed a cropped capture of the source's chart with a source line, link, and date; in a public one, redraw it from the published figures or get permission.
- **Bold for skimming**: bold the take-home message, each section's opening sentence, and about one key phrase in other paragraphs, so the bold text alone tells the argument; more bold defeats it.

Before:

> We compared list prices from both vendors. Argon is cheaper until 30 November, after which the prices are the same, so the choice depends on token use.

After:

> We compared list prices from both vendors. **Argon is cheaper until 30 November**; after that **the prices are the same, so token use decides the cost**.

## Links and sensitivity

Links let the reader check a claim and follow up, so link generously, inline, where the reader needs them: vendor documentation, standards, and primary sources rather than articles about them, plus the internal documents, tickets, and dashboards the user provides. When an internal page exists but you lack its address, write a visible placeholder such as `{link to the usage dashboard}`.

Before adding a link, ask whether this reader can open it and should see what it reveals:

- **Link only what the reader can access**: a client's wiki suits the client's team, not a vendor or the public; a dead or login-walled link reads as noise.
- **Read the URL as content**: hostnames, project, customer, or person names, folder paths, and ticket titles disclose information even when the page is locked; describe the source in words instead when the URL says too much.
- **Never share access by accident**: drop tokens, signed or expiring URLs, and "anyone with the link" shares unless the user meant to grant that access.
- **Keep our own workspace out**: brain notes, local paths, session or agent links, and private repositories stay out of client and public documents.

## Destination and platform features

A designed document is easier to read and earns trust, so make it beautiful by default: color in headings, the summary card, key-figure tiles, status badges, and framed figures, generous spacing, body text of at least 16 px on screen and 10 pt in print, and a layout that survives phone widths and printing. Use the Fmind design or the client's brand, and prefer each platform's native features to hand-built imitations, because they render, navigate, and stay editable as the reader expects:

- **Standalone HTML**: the [report template](../templates/report.html), self-contained with embedded fonts and images so it renders the same offline and through email gateways.
- **Markdown**: the [Markdown template](../templates/report.md), adapted to the renderer as its header comment explains.
- **Zensical sites**: admonitions for take-home boxes and warnings, content tabs for per-option detail, Mermaid diagrams, collapsible blocks for annexes, and the abbreviations glossary as Key terms tooltips ([authoring](../../documentation-site/references/authoring.md)).
- **GitHub Markdown**: `> [!IMPORTANT]` alerts for the ask, Mermaid diagrams, `<details>` blocks for annexes, and task lists for next steps.
- **Google Docs**: native Drive Markdown (`.md`, `mimeType: text/markdown`) by default via [draft-doc](../../draft-doc/SKILL.md) — ATX `#`–`######` headings for the document outline, native GFM tables, interactive checklists (`- [ ]`), LaTeX equations (`$...$` / `$$...$$`), footnotes (`[^1]`), inline comments, and `@2x` Mermaid/SVG figures compiled to bottom `[fig-N]: <data:image/png;base64,...>` reference definitions (no YAML frontmatter, no `> [!IMPORTANT]` alerts, no raw HTML tags). Use converted Google Docs (`application/vnd.google-apps.document`) via [gws](../../gws/SKILL.md) only when multiple Document Tabs or Docs-native smart chips are required.
- **Email and chat**: plain text or light formatting that the client shows reliably, with no external images; Slack and Chat support only a small Markdown subset.

## Honest framing

- **State confidence and its basis**: "high confidence: measured on production traffic" or "low confidence: list prices only, no load test yet".
- **Name what was not checked**: and what result would change the recommendation.
- **Stay neutral**: describe every option with the same criteria, sources, and tone, report the evidence that favors the option you do not recommend, and say when the evidence is not comparable, such as benchmarks run at different settings.
- **Avoid unsupported superlatives**: "best", "seamless", "guaranteed", and "secure" need evidence or must go.
