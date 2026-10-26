# Style for Busy Readers

Apply these rules to every document written for people outside the session. Where a rule is easy to misread, a before and after example follows it.

## Plain, literal language

Write complete sentences with a subject and a verb. Prefer everyday words to jargon and the active voice to the passive. Replace arrows, slash chains, stacked parentheses, and coined labels with sentences, and expand each acronym at first use.

Before:

> Batch → spot VMs ≈ -60% compute (preemptible, w/ retries); SLA risk ↑.

After:

> Running the nightly batch jobs on spot virtual machines would cut their compute cost by about 60%. Google can reclaim these machines at short notice in exchange for the lower price. The jobs already retry automatically, so a reclaimed machine delays a job by minutes rather than failing it. The main risk is missing the 7:00 report deadline when many machines are reclaimed at once.

## Terms and metrics

List the terms, units, and metrics this reader may not know in a **Key terms** block right after the executive summary, one short line each, so the reader meets them before the body uses them. For a metric, say what it measures, its unit, and which direction is better; give its baseline where you use it. Units and plain terms need no direction. Skip terms this reader uses daily, such as CVE for a security team. A short email or chat message defines its one or two terms inline instead.

Before:

> p95 dropped to 400 ms.

After, with this line in Key terms:

> **p95 latency**: the time within which 95% of requests finish, in seconds; lower is better.

And this sentence in the body:

> The p95 latency fell from 1.2 s to 0.4 s after the change. We measured it over 10,000 requests in the week of 6 October.

## Numbers

- **Give the context of every figure**: unit, currency, period, region, and price date, such as "€4,200 per month at October 2026 list prices in the europe-west1 region".
- **Round to what the inputs support**: write "about €4,000 to €5,000 per month" for an estimate, not "€4,213.57".
- **Show conservative ranges for estimates**: say which input drives the range, and show the result at both ends.
- **Separate percent from percentage points**: "the error rate fell from 4% to 3%, one percentage point or a 25% reduction".
- **Compare with a baseline**: "30% cheaper than today's spend on the managed service, at today's volume".
- **Follow the reader's conventions**: in French, write "4 200 €" and use a decimal comma.

## Titles, headings, and section summaries

Titles and headings are short names that help the reader navigate; the conclusion goes in the bold first sentence of the section, where it has room to be precise.

| Element        | Before                                                                  | After                                                                                 |
| -------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Title          | Spot machines cut batch costs by 60%, with a small risk of late reports | Moving batch jobs to spot machines                                                    |
| Heading        | Moving the jobs keeps all data in the EU but adds two service accounts  | Security                                                                              |
| First sentence | We reviewed the security of the move.                                   | **Moving the jobs keeps all data in the EU but adds two service accounts to manage.** |

Put the document's metadata at the top, one field per line, instead of one long line:

> Type: Decision memo\
> Status: Draft\
> Audience: Engineering and product leads\
> Author: {name}\
> Date: 26 October 2026

Close a long section with a short box titled "Take-home messages", in one to three sentences, so a reader who skimmed the section still leaves with its point:

> **Take-home messages**: from December, the two models cost the same per token, so the pilot's measure of tokens per task decides the cheaper option.

## Examples, tables, and visuals

- **Make abstract claims concrete**: "for example, the invoice job that runs at 2:00 and takes 40 minutes".
- **Use a table for every comparison**: put options or periods in rows and the same criteria in columns, number the options, and mark the recommended row.
- **Flag ratings with a colored status and a word**: Low, Medium, and High for risk, or Met, Partial, and Not met for requirements, in green, amber, and red, so limitations and issues stand out in tables. In HTML, use the template's status badges, because emoji depend on the reader's fonts and can render blank; in Markdown and chat, use 🟢, 🟡, and 🔴. Never use the color alone, and keep status marks out of running prose.
- **Prefer a figure to a paragraph**: use a chart for numbers and trends and a diagram for a flow, an architecture, or a timeline; give each a caption that states its conclusion, not its topic. Show benchmark or survey results as a chart with a source line, never as a sentence that lists five numbers.
- **Bold for skimming**: bold the take-home message, the conclusion sentence that opens each section, and one key phrase in other paragraphs, so the bold text alone tells the argument; bolding more than that defeats it.

Before:

> We compared list prices from both vendors. Argon is cheaper until 30 November, after which the prices are the same, so the choice depends on token use.

After:

> We compared list prices from both vendors. **Argon is cheaper until 30 November**; after that **the prices are the same, so token use decides the cost**.

## Links for follow-up

Link each figure, claim, and process to the page that supports it, inline, where the reader needs it: vendor documentation, standards, and the internal documents, tickets, and dashboards the user provides. Prefer primary sources to articles about them. When an internal page exists but you do not have its address, write a visible placeholder such as `{link to the usage dashboard}` for the user to fill.

## Honest framing

- **State confidence and its basis**: "high confidence: measured on production traffic" or "low confidence: list prices only, no load test yet".
- **Name what was not checked**: and what result would change the recommendation.
- **Stay neutral**: describe every option with the same criteria, sources, and tone; report the evidence that favors the option you do not recommend.
- **Avoid unsupported superlatives**: "best", "seamless", "guaranteed", and "secure" need evidence or must go.
