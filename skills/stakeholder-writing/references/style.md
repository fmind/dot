# Style for Busy Readers

Apply these rules to every document written for people outside the session. Each rule shows a before and after example.

## Plain, literal language

Write complete sentences with a subject and a verb. Prefer everyday words to jargon and the active voice to the passive. Replace arrows, slash chains, stacked parentheses, and coined labels with sentences, and expand each acronym at first use.

Before:

> Batch → spot VMs ≈ -60% compute (preemptible, w/ retries); SLA risk ↑.

After:

> Running the nightly batch jobs on spot virtual machines would cut their compute cost by about 60%. Google can reclaim these machines at short notice in exchange for the lower price. The jobs already retry automatically, so a reclaimed machine delays a job by minutes rather than failing it. The main risk is missing the 7:00 report deadline when many machines are reclaimed at once.

## Terms and metrics

Define each metric once, at first use: what it measures, its unit, which direction is better, and the baseline it is compared with. Units and plain terms need no direction. Skip definitions of terms this reader uses daily, such as CVE for a security team. Add a glossary annex when the document needs more than five definitions.

Before:

> p95 dropped to 400 ms.

After:

> The p95 latency, the time within which 95% of requests finish, fell from 1.2 s to 0.4 s after the change (lower is better). We measured it over 10,000 requests in the week of 6 October.

## Numbers

- **Give the context of every figure**: unit, currency, period, region, and price date, such as "€4,200 per month at October 2026 list prices in the europe-west1 region".
- **Round to what the inputs support**: write "about €4,000 to €5,000 per month" for an estimate, not "€4,213.57".
- **Show ranges for estimates**: say which input drives the range, and show the result at both ends.
- **Separate percent from percentage points**: "the error rate fell from 4% to 3%, one percentage point or a 25% reduction".
- **Compare with a baseline**: "30% cheaper than today's spend on the managed service, at today's volume".
- **Follow the reader's conventions**: in French, write "4 200 €" and use a decimal comma.

## Headings that carry the message

A reader who skims only the headings should get the story.

| Before        | After                                                                      |
| ------------- | -------------------------------------------------------------------------- |
| Cost analysis | Spot machines cut batch costs by 60%, with a small risk of late reports    |
| Security      | Moving the jobs keeps all data in the EU but adds two service accounts     |
| Next steps    | A two-week pilot in November can confirm the savings before any commitment |

## Examples, tables, and visuals

- **Make abstract claims concrete**: "for example, the invoice job that runs at 2:00 and takes 40 minutes".
- **Use a table for every comparison**: put options or periods in rows and the same criteria in columns, and mark the recommended row.
- **Use a chart for a trend and a diagram for a flow**: give each a caption that states its conclusion, not its topic.
- **Bold sparingly**: bold the take-home message and the few phrases a skimming reader must not miss.

## Honest framing

- **State confidence and its basis**: "high confidence: measured on production traffic" or "low confidence: list prices only, no load test yet".
- **Name what was not checked**: and what result would change the recommendation.
- **Avoid unsupported superlatives**: "best", "seamless", "guaranteed", and "secure" need evidence or must go.
