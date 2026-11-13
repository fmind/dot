---
name: draft-typst-deck
description: Create 16:9 Typst executive PDF slide decks with pure-Typst charts, overflow and font verification, and isolated gws Drive upload.
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-typst-deck
  created: "2026-11-13"
  updated: "2026-11-13"
---

# Draft Typst Slide Deck

Produce calm, high-contrast **16:9 (`960pt x 540pt`) Typst PDF slide decks** paired with editable `.typ` sources, fixed-height layout primitives, pure-Typst comparative visuals, overflow/font checks, and optional Google Drive upload via [gws](../gws/SKILL.md). Apply the Fmind Theme (`~/.agents/DESIGN.md`, light `#FFFFFF` canvas, `#174EA6` primary accent, `Google Sans` + `Google Sans Code`) by default, or substitute a client's brand tokens and fonts when working for a customer (never mix brands).

## When to Use vs Sibling Skills

- Use **`draft-typst-deck`** when stakeholders need a concise, fixed-pagination **PDF slide deck** compiled deterministically from readable `.typ` sources ([fmind-slides.typ](templates/fmind-slides.typ), [deck.typ](templates/deck.typ)).
- Use [stakeholder-writing slides guidance](../stakeholder-writing/references/slides.md) when an HTML/CSS or Google Slides deck is preferred, or when structuring story arcs and comparison tables.
- Use [draft-doc](../draft-doc/SKILL.md) for narrative Google Docs reports and memos (`gws` native Markdown `.md`).

## Deck Architecture & Layout Budgets

1. **Keep `.typ` sources beside the compiled PDF**: copy [fmind-slides.typ](templates/fmind-slides.typ) and [deck.typ](templates/deck.typ) into the target directory so `--root` resolves imports offline with zero external `@preview/...` packages.
1. **Strict density ceiling**: aim for `4–8` slides (`25–45` words per slide, max `3–4` short bullets per card, zero crowded prose). Put detail tables or methodology formulas into backup slides or linked memos.
1. **Readable typography & spacing**: titles `26pt` (`38pt` cover), body/cards `15.5–16pt`, comparative bar labels `>=12pt` (`11.5pt` floor only on dense sub-captions), generous padding, and fixed card heights (`128pt`, `164pt`) to prevent vertical spill.
1. **At most 3 comparative visuals per deck**: use pure-Typst `bar-panel`, `stacked-bar-row`, `broken-bar-row`, `step-card`, and `flow-arrow` helpers documented in [charts-and-diagrams.md](references/charts-and-diagrams.md). Follow [charts-and-diagrams.md#typst-escaping-rules](references/charts-and-diagrams.md#typst-escaping-rules) (`$`, `~`, `*` differ between `"..."`, `` `...` ``, and `[...]`).

## Workflow (`check`, visual inspection, `upload`)

Run [build_typst_deck.py](scripts/build_typst_deck.py) via isolated Python stdlib (`python3 -I`) — no third-party dependencies or network fetches required:

1. **Validate escaping, compile PDF + PNGs, and verify exact slide count**:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py check deck.typ \
     --expected-slides 4 --json
   ```

   Pass `--render-figures` when standalone diagrams live in `figures/*.typ`. The gate fails on unexpected escapes (`\$`, `\~`, `\*` in strings/backticks), empty bold stars (`**...**`), `unknown font family` warnings, or any slide count mismatch (`Overflow/mismatch`).

1. **Inspect every PNG slide before sharing**: read `_preview/<stem>-1.png` .. `_preview/<stem>-N.png` and complete the pre-share checklist in [verification-and-drive.md](references/verification-and-drive.md).

1. **Dry-run and upload to Google Drive (only after user sign-off)**:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py upload deck.pdf \
     --file-id "<FILE_ID>" --dry-run --json
   ```

   Then rerun without `--dry-run` (or use `--drive-folder "<FOLDER_ID>"` to create/upsert by name, plus `--protect-copy` to restrict viewer downloads). Upload stages the PDF in a private temp directory, verifies `%PDF-` magic bytes, and checks remote `md5Checksum` + byte size parity before reporting success.
