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

- **Gmail HTML (`draft-mail`)**: Gmail strips `<style>`; inline Fmind tokens (`#202124` ink, `#174EA6` accent, `#F1F3F4` panel, `#D2E3FC` selection, `#0D652D`/`#CEEAD6` ok, `#934900`/`#FEEFC3` risk, `#A50E0E`/`#FAD2CF` blocker) inside `max-width: 640px`:

```html
<div style="font-family: 'Google Sans', Arial, sans-serif; color: #202124; max-width: 640px; line-height: 1.5;">
  <p style="margin: 0 0 12px; padding: 12px 14px; background: #D2E3FC; border-left: 4px solid #174EA6; border-radius: 8px;">
    <strong style="color: #174EA6;">Decision needed:</strong> Approve the Q4 vendor switch by Thursday 17:00 CET.
  </p>
  <p style="margin: 0 0 12px;">
    Consolidating onto Provider B cuts compute spend by
    <mark style="background: #CEEAD6; color: #0D652D; padding: 1px 6px; border-radius: 4px; font-weight: 600;">38% ($42k/year)</mark>
    with zero migration downtime.
  </p>
  <hr style="border: 0; border-top: 1px solid #9AA0A6; margin: 16px 0;" />
  <p style="margin: 0; color: #595D62; font-size: 13px;">Next check-in: Friday 10:00 CET unless you raise objections.</p>
</div>
```

- **Google Docs (`draft-doc`)**:
  - _Native `.md`_: use `---` rules, 3–4 column tables, bold lead-ins, bold-label blockquotes, and compiled `≤440pt` Typst PNG cards (`diagrams-as-code`, `draft-doc/references/dialect.md`); raw HTML tags render literally.
  - _Styled HTML_: for `<mark>` highlights, tinted banners, or shaded tables, import via `gws drive files create --json '{"name":"<Title>","mimeType":"application/vnd.google-apps.document"}' --upload <file.html> --upload-content-type text/html`.

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
