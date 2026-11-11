# Style for Busy Readers

Defaults for external readers; adapt when the reader or destination calls for it.

## Plain, literal language

Write active sentences with everyday words and one idea per short paragraph. Replace arrows, slash chains, stacked parentheses, and coined labels with prose, and expand acronyms at first use.

Before: `Batch → spot VMs ≈ -60% compute (preemptible, w/ retries); SLA risk ↑.`

After:

> Running nightly batch jobs on spot virtual machines cuts compute cost by about 60%. Google can reclaim these machines at short notice, delaying retried jobs by minutes rather than failing them. The main risk is missing the 7:00 report deadline if many machines are reclaimed at once.

## Code formatting

Use code formatting only for commands, paths, or literal values the reader must copy—never for product names, concepts, or non-technical readers (write "the invoice export writes to the EU bucket for 30 days", not `` `invoice_export` writes to `exports-eu` with `retention_days=30` ``).

## Terms and metrics

Define one or two essential terms inline. In formal documents, put other unfamiliar terms, units, and metrics in a **Key terms** annex (one line each) and skip daily team vocabulary (such as CVE for security). State each metric's meaning, unit, better direction (`**p95 latency**: time within which 95% of requests finish, in seconds; lower is better`), and inline baseline (`fell from 1.2 s to 0.4 s over 10,000 requests in the week of 6 October`). Short documents, emails, and chat define terms inline.

## Numbers

- **Give full context**: unit, currency, period, region, and price date ("€4,200/month at October 2026 list prices in europe-west1").
- **Round to input precision**: "about €4,000 to €5,000 per month", not "€4,213.57".
- **Show conservative ranges**: name the driving input and give both ends.
- **Separate percent from percentage points**: "fell from 4% to 3% (1 percentage point, a 25% reduction)".
- **Compare against a baseline**: "30% cheaper than today's managed-service spend at current volume".
- **Match reader locale**: in French, write "4 200 €" and use a decimal comma.

## Titles, headings, and section summaries

Keep titles and headings short and literal for navigation ("Context", "Options", "Security", "Next steps"). Put the conclusion in the section's bold first sentence, never in the heading.

| Element        | Before                                                                  | After                                                                                 |
| -------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Title          | Spot machines cut batch costs by 60%, with a small risk of late reports | Moving batch jobs to spot machines                                                    |
| Heading        | Moving the jobs keeps all data in the EU but adds two service accounts  | Security                                                                              |
| First sentence | We reviewed the security of the move.                                   | **Moving the jobs keeps all data in the EU but adds two service accounts to manage.** |

When a formal document needs metadata at the top, list one field per line: `Type`, `Status` (Draft/Final), `Audience`, `Author`, and `Date`. Close long or multi-finding sections with a 1–3 sentence `**Take-home messages**: ...` box; short sections need none.

## Examples, tables, and visuals

- **Ground abstract claims**: "for example, the 2:00 invoice job that runs for 40 minutes".
- **Compare in tables**: options or periods in rows, shared criteria in columns, user labels preserved, and the recommended row marked.
- **Pair color with words**: `Low` / `Medium` / `High` or `Met` / `Partial` / `Not met` in green, amber, and red. Use CSS badges in HTML (emoji vary across fonts) and 🟢 🟡 🔴 in Markdown or chat; keep status marks out of running prose.
- **Draw figures when faster than prose**: use SVG, Mermaid, or matplotlib—charts for trends and numbers, diagrams for flows, architectures, or timelines ([diagrams-as-code](../../diagrams-as-code/SKILL.md)). Put key figures in the body and supporting ones in annexes, each with a conclusion caption plus a table or text alternative.
- **Cite third-party figures properly**: private team docs may embed a cropped capture with source, link, and date; public docs must redraw from published data or obtain permission.
- **Bold for skimming**: bold the take-home message, each section's opening sentence, and at most one key phrase per paragraph so the bold text alone carries the argument.

## Links and sensitivity

Link claims inline to primary docs, standards, and user-provided internal pages rather than secondary articles; mark missing internal URLs with plain placeholders like `{link to the usage dashboard}`. Before linking, check reader access and URL exposure:

- **Link only accessible pages**: skip client wikis in vendor or public docs; dead or login-walled links read as noise.
- **Inspect URL text**: hostnames, customer or person names, paths, and ticket slugs leak context even when locked—describe the source in prose instead.
- **Strip unintended access**: never include tokens, signed/expiring URLs, or link-sharing grants unless authorized.
- **Exclude session workspace**: keep brain notes, local paths, session/agent links, and private repos out of client and public deliverables.

## Destination and platform features

Design formal documents cleanly by default: colored headings, summary card, key-figure tiles, status badges, framed figures, ≥16 px screen / ≥10 pt print body type, and responsive/print-safe layout. Apply `~/.agents/DESIGN.md` (Fmind Theme) or customer branding, using each platform's native primitives:

- **Standalone HTML**: [report template](../templates/report.html), self-contained with embedded WOFF2 fonts and data-URI images for offline and email-gateway safety.
- **Markdown**: [Markdown template](../templates/report.md), adapted to the target renderer.
- **Zensical sites**: admonitions, content tabs, Mermaid fences, collapsible annexes, and glossary tooltips ([authoring](../../documentation-site/references/authoring.md)).
- **GitHub Markdown**: `> [!IMPORTANT]` alerts, Mermaid fences, `<details>` annexes, and task lists.
- **Google Docs**: [draft-doc](../../draft-doc/SKILL.md#format-choice) selects native `.md` vs `.gdoc` and enforces [native `.md` dialect rules](../../draft-doc/SKILL.md#native-md-dialect-rules).
- **Email and chat**: short paragraphs, no headings, no external images, and at most one short list within Slack/Chat Markdown limits.

## Honest framing

- **Ground confidence**: "high confidence: measured on production traffic" or "low confidence: list prices only, no load test".
- **State gaps and flip conditions**: name what was not checked and what finding would change the recommendation.
- **Stay neutral**: apply identical criteria and tone to every option, include counter-evidence, and flag non-comparable benchmarks.
- **Cut unsupported superlatives**: drop "best", "seamless", "guaranteed", or "secure" without proof.
