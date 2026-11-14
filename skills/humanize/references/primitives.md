# Visual Primitives and Rewrites

Select only primitives supported by the target renderer. Never paste raw HTML into Slack, GitHub alerts into Zensical, or raw Markdown tables into Gmail plain text.

## Before and after

<details>
<summary>Engineering status update: AI dump vs scannable update</summary>

Before (92 words, jargon, backticks everywhere):

> I finished investigating the `ingest-worker` pod OOMKilled (`exit code 137`) during `batch_run_42`. After reading `memory_profiler` traces in `src/worker/loader.py`, `polars.read_parquet` materialized a `4.2 GB` DataFrame because `chunk_size` defaulted to `None` inside `LoaderSettings`. I patched `chunk_size=100_000` in PR `#418`, bumped the Cloud Run memory limit to `8 GiB` in `infra/main.tf`, and verified `pytest tests/test_loader.py` passed (`14 passed`). Please review PR `#418` and approve the Cloud Run deployment.

After (44 words, zero jargon, 1 highlight, 1 clear ask):

> **Summary: Nightly data ingestion is healthy again — approve the fix so tonight's run completes.**
>
> Batch imports hit a memory ceiling at 4.2 GB and restarted automatically. Streamed loading now caps peak usage well below the new 8 GB limit.
>
> **Decision needed:** Approve [pull request 418](https://example.com/org/repo/pull/418) before 17:00 UTC.

</details>

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

- **Gmail HTML (`draft-mail`)**: Gmail strips `<style>` blocks; inline Fmind colors (`#202124` ink, `#174EA6` accent, `#F1F3F4` panel, `#D2E3FC` selection highlight, `#0D652D`/`#CEEAD6` success, `#934900`/`#FEEFC3` risk, `#A50E0E`/`#FAD2CF` blocker) and stack short blocks inside `max-width: 640px`.

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
  - _Native editable doc path_: author clean Markdown with `---` horizontal rules, compact 3–4 column tables, bold lead-ins, `[!CALLOUT]` blocks (bold label blockquote), and compiled `≤440pt` Typst PNG cards (`diagrams-as-code`, `draft-doc/references/dialect.md`) because Google Docs ignores raw HTML `<mark>` and `<span>` styles inside imported `.md`.
  - _Styled HTML import path_: when colored highlights (`<mark style="background:#D2E3FC">`), tinted summary banners, or exact column shading matter more than editing Markdown later, upload styled HTML with `--mime-type text/html` converted to `application/vnd.google-apps.document` via `gws`.

- **GitHub PRs, issues, & READMEs (`gh`, `repository-docs`)**: use GitHub-Flavored alerts, bold status pills, short tables, and `<details>` for noisy command output or secondary rationale.

```markdown
> [!IMPORTANT]
> **Approve before 17:00 UTC:** switches storage backend to cut monthly spend by 40%.

**Status:** Passed · **Scope:** 3 service modules

<details>
<summary>Verification details (optional reading)</summary>

Suite ran against staging snapshot at 14:20 UTC with zero regressions.

</details>
```

- **Zensical docs & portals (`documentation-site`)**: Zensical renders Material/PyMdown extensions rather than GitHub `[!IMPORTANT]` alerts. Use highlight marks, admonitions, collapsible blocks, tabbed views, and card grids cleanly:

```markdown
Spend drops ==38% this quarter== after consolidating the cluster.

!!! success "Decision ready" Approve the cutover window before Thursday 17:00 CET.

??? info "Detailed benchmarks" Median latency stayed at 42 ms across 10,000 requests.
```

- **Jira & Confluence (`acli`)**: author native ADF panels (`info`, `note`, `warning`, `success`, `error`), status lozenges, tables, and expand macros rather than raw Markdown strings.

- **Slides (`draft-typst-deck`)**: target one visual focal point and at most 30 visible words per slide using `#hl[...]`, `#pill[...]`, `#callout[...]`, `#kpi-row(...)`, `#bar-panel(...)`, `#split-cards(...)`, `#card(...)`, and `#brand-card(...)`; move context and caveats into `#speaker-note[...]`.

- **Chat & Slack (`gws` Chat)**: limit posts to 80 words or fewer, lead with a bold one-line ask or outcome, separate points into short bullets, and use a single `---` rule when needed.

## Framing, numbers, and scannability

- **Executive / customer lens**: trade metrics in time, money, risk, reliability, or adoption. Never paste raw stack traces, internal branch names, or database columns in customer or leadership copy.
- **Peer engineer lens**: link exact PRs, files, or dashboards cleanly inline without breaking flow with verbose path lists inside sentences.
- **Honest rounding**: round `98.742%` to `99%`, `$41,892` to `$42k`, `382 ms` to `0.4 s`, always paired with its baseline or limit (`0.4 s vs 1.5 s SLA`).
- **Paragraph rhythm**: cap paragraphs at 3 lines; give every list item a **Bold lead-in**; leave visible whitespace between headline, takeaway, evidence visual, and ask.
