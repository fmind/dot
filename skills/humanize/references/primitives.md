# Visual Primitives and Rewrites

Select only primitives supported by the target renderer. Never paste raw HTML into Slack, GitHub alerts into Zensical, or raw Markdown tables into Gmail plain text.

## Before and after

<details>
<summary>Executive incident memo: timeline wall vs table + badge</summary>

Before:

> At 09:12 UTC `checkout-api` returned `502 Bad Gateway` for `eu-west1` users because `pg_pool_max` (`20`) saturated under promo traffic spikes while `read_replica_enabled` was `false`. Mitigation scaled instances from `2` to `6`, raised `pg_pool_max` to `60`, and enabled `read_replica_enabled=true` at 09:27 UTC. Total impact was 15 minutes (`~1.8%` failed checkouts).

After:

> **Resolved: European checkout errors lasted 15 minutes; database capacity is tripled before tonight's peak.**
>
> **Status:** Recovered · **Impact:** under 2% of European checkouts failed between 09:12 and 09:27 UTC.
>
> | Area                 | Previous limit      | Current headroom    | Follow-up            |
> | :------------------- | :------------------ | :------------------ | :------------------- |
> | Database connections | Saturated at 20     | **60 active slots** | Alert at 75% load    |
> | Read traffic         | Single primary node | **Replica enabled** | Add load test Friday |

</details>

## Channel primitives

- **Gmail HTML (`draft-mail`)**:
  - _Default (routine emails, replies, scheduling, admin)_: plain `<p>`, `<strong>`, `<ul>`/`<ol>`, and `<a href="...">` so the message matches native Gmail compose and `.gmail_signature` without newsletter chrome:

    ```html
    <p>Bonjour Alice,</p>
    <p><strong>We can switch to Provider B on Thursday, 19 November at 17:00 CET</strong> with zero downtime and $42k/year lower compute spend (38% below Q3).</p>
    <ul>
      <li><strong>Action needed:</strong> confirm the maintenance window by Wednesday 12:00 CET.</li>
      <li><strong>Rollout plan:</strong> <a href="https://example.com/runbook">cutover runbook</a>.</li>
    </ul>
    <p>Best,<br>Médéric</p>
    ```

  - _Executive/incident briefs only (skip on routine mail; pick at most one accent, never stack a banner with `<mark>`)_: Gmail strips `<style>`, so inline Fmind tokens (`#202124` ink, `#174EA6` accent, `#F1F3F4` neutral panel, `#D2E3FC` selection, `#0D652D`/`#CEEAD6` ok, `#934900`/`#FEEFC3` risk, `#A50E0E`/`#FAD2CF` blocker):

    ```html
    <p style="margin: 0 0 12px; padding: 10px 14px; background: #F1F3F4; border-left: 3px solid #174EA6; border-radius: 6px;">
      <strong>Decision needed by Thursday 17:00 CET:</strong> approve the Q4 vendor switch ($42k/year savings).
    </p>
    ```

- **Google Docs (`draft-doc`)**: let the user choose standard `.gdoc` vs Markdown `.md` ([format choice](../../draft-doc/SKILL.md#format-choice)):
  - _Standard `.gdoc`_ (high customization for polished reports): inline-styled HTML import (`<mark>`, 1-cell tinted callout tables, shaded table rows, Base64 Typst PNGs) or `documents.batchUpdate` (`draft-doc/references/gdoc.md`).
  - _Markdown `.md`_ (simpler to produce/update, low customization): `---` rules, 3–4 column tables, bold lead-ins, bold-label blockquotes, and compiled `≤440pt` Typst PNG cards (`diagrams-as-code`, `draft-doc/references/dialect.md`); raw HTML tags render literally.

- **GitHub PRs, issues, & READMEs (`gh`, `repository-docs`)**: pair GFM alerts, bold status pills, short tables, and `<details>` for logs:

```markdown
> [!IMPORTANT]
> **Approve before 17:00 UTC:** switches storage backend to cut monthly spend by 40%.

**Status:** Passed · **Scope:** 3 service modules

<details>
<summary>Verification details (optional reading)</summary>

Suite ran against staging snapshot at 14:20 UTC with zero regressions.

</details>
```

- **Zensical (`documentation-site`)**: Material/PyMdown syntax (not `[!IMPORTANT]`); indent bodies 4 spaces under headers:

```text
Spend drops ==38% this quarter== after consolidating the cluster.

!!! success "Decision ready"
    Approve the cutover window before Thursday 17:00 CET.

??? info "Detailed benchmarks"
    Median latency stayed at 42 ms across 10,000 requests.
```

- **Jira & Confluence (`acli`)**: author native ADF panels (`info`, `note`, `warning`, `success`, `error`), status lozenges, tables, and expand macros rather than raw Markdown strings.

- **Slides (`draft-typst-deck`)**: target one visual focal point and at most 30 visible words per slide using `#hl[...]`, `#pill[...]`, `#callout[...]`, `#kpi-row(...)`, `#bar-panel(...)`, `#split-cards(...)`, `#card(...)`, and `#brand-card(...)`; move context and caveats into `#speaker-note[...]`.

- **Chat & Slack (`gws` Chat)**: limit posts to 80 words or fewer, lead with a bold one-line ask or outcome, separate points into short bullets, and use a single `---` rule when needed.

## Framing, numbers, and scannability

- **Executive / customer lens**: trade metrics in time, money, risk, reliability, or adoption; omit raw stack traces, branch names, and DB columns.
- **Peer engineer lens**: link PRs, files, or dashboards cleanly inline without breaking flow.
- **Honest rounding**: round `98.742%` → `99%`, `$41,892` → `$42k`, `382 ms` → `0.4 s`, paired with a baseline or limit (`0.4 s vs 1.5 s SLA`).
