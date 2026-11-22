# Visual Primitives and Rewrites

Pick only primitives supported by the target renderer. Never paste raw HTML into Slack, GitHub alerts into Zensical, or raw Markdown tables into plain-text Gmail.

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

- **Gmail HTML ([draft/mail](../../draft/references/mail/GUIDE.md))**:
  - _Default (routine mail, replies)_: plain `<p>`, `<strong>`, `<ul>`/`<ol>`, and `<a href="...">` matching `.gmail_signature` without newsletter chrome:

    ```html
    <p>Hi Alice,</p>
    <p><strong>We can switch to Provider B on Thursday, 19 November at 17:00 CET</strong> with zero downtime and $42k/year lower compute spend (38% below Q3).</p>
    <ul>
      <li><strong>Action needed:</strong> confirm the maintenance window by Wednesday 12:00 CET.</li>
      <li><strong>Rollout plan:</strong> <a href="https://example.com/runbook">cutover runbook</a>.</li>
    </ul>
    <p>Best,<br>Médéric</p>
    ```

  - _Executive/incident briefs only (skip on routine mail; max 1 accent, never stack banner + `<mark>`)_: inline Fmind tokens (`#202124` ink, `#174EA6` accent, `#F1F3F4` neutral, `#D2E3FC` selection, `#0D652D`/`#CEEAD6` ok, `#934900`/`#FEEFC3` risk, `#A50E0E`/`#FAD2CF` blocker):

    ```html
    <p style="margin: 0 0 12px; padding: 10px 14px; background: #F1F3F4; border-left: 3px solid #174EA6; border-radius: 6px;">
      <strong>Decision needed by Thursday 17:00 CET:</strong> approve the Q4 vendor switch ($42k/year savings).
    </p>
    ```

- **Google Docs ([draft/doc](../../draft/references/doc/GUIDE.md))**: confirm `.gdoc` vs `.md` ([format choice](../../draft/references/doc/GUIDE.md#format-choice)):
  - _Standard `.gdoc`_: inline-styled HTML (`<mark>`, 1-cell callout tables, shaded rows, Base64 PNGs) or `documents.batchUpdate` ([gdoc](../../draft/references/doc/references/gdoc.md)).
  - _Markdown `.md`_: `---` rules, 3–4 column tables, bold lead-ins/blockquotes, and `<=440pt` compiled PNGs (`diagrams-as-code`, [dialect](../../draft/references/doc/references/dialect.md)); raw HTML renders literally.

- **GitHub ([github](../../github/SKILL.md), [docs/repository](../../docs/references/repository/GUIDE.md))**: GFM alerts, status pills, short tables, and `<details>`:

```markdown
> [!IMPORTANT]
> **Approve before 17:00 UTC:** switches storage to cut spend 40%.

**Status:** Passed · **Scope:** 3 modules

<details>
<summary>Verification</summary>

Staging snapshot passed at 14:20 UTC with zero regressions.

</details>
```

- **Zensical ([docs/site](../../docs/references/site/GUIDE.md))**: Material/PyMdown syntax (not `[!IMPORTANT]`); indent bodies 4 spaces:

```text
Spend drops ==38% this quarter== after consolidating the cluster.

!!! success "Decision ready"
    Approve cutover before Thu 17:00 CET.

??? info "Benchmarks"
    Median latency stayed at 42 ms across 10k requests.
```

- **Jira & Confluence ([cloud-ops/acli](../../cloud-ops/references/acli.md))**: native ADF panels (`info`, `note`, `warning`, `success`, `error`), lozenges, tables, and expand macros—never raw Markdown.
- **Slides ([draft/typst-deck](../../draft/references/typst-deck/GUIDE.md), [draft/slides](../../draft/references/slides/GUIDE.md))**: one focal visual and ~30 visible words (~45 on charts with units and `N`); in Typst use `#hl[...]`, `#pill[...]`, `#callout[...]`, `#kpi-card(...)`, `#bar-panel(...)`, `#split-cards(...)`, `#card(...)`, `#step-card(...)`, and `#flow-arrow(...)` (`#show: brand-card.with(...)` for standalone cards only), putting caveats in speaker notes.
- **Sheets ([draft/sheets](../../draft/references/sheets/GUIDE.md))**: frozen bold header row, explicit currency/percent/date formats, right-aligned numbers, and separate `RAW` inputs vs explicit formula cells.
- **Chat & Slack ([gws/chat](../../gws/references/chat.md))**: `<= 60–80` words (`3–5` lines): bold ask/outcome, 2–3 plain bullets, and sources/caveats/links in a thread reply.
