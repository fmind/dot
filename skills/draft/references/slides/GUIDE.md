---
name: slides
description: "Create or update native editable Google Slides via gws slides and Drive upload."
---

# Draft Google Slides

Native editable Google Slides plumbing via [gws](../../../gws/SKILL.md) (`gws slides`) and [`drive_upload.py`](../../../gws/scripts/drive_upload.py). For pixel-perfect Typst PDF/Retina decks, use [draft/typst-deck](../typst-deck/GUIDE.md). Delegate narrative, slide density, and brand tokens to [humanize](../../../humanize/SKILL.md), customer brand or `~/.agents/DESIGN.md`, and [diagrams-as-code](../../../diagrams-as-code/SKILL.md).

## Authoring Paths

1. **Client template copy + `replaceAllText` (preferred when a brand master exists)**: copy the template via `gws drive files copy` with explicit `parents: ["<FOLDER_ID>"]` (overrides source ACLs), then patch placeholders via `gws slides presentations batchUpdate`.
1. **Native Slides API (`presentations.create` + `batchUpdate`)**: adapt the starter [draft_slides.py](templates/draft_slides.py) to create a presentation, move/target a folder, apply `batchUpdate` requests (`createSlide`, `createShape`, `insertText`, `updateTextStyle`), and read back slide count.
1. **Private local images in editable Slides**: `gws slides` `createImage` requires a public HTTPS URL—never publish private figures. Build an editable `.pptx` with `uv run --with python-pptx` embedding local PNGs, then convert privately via [`drive_upload.py`](../../../gws/scripts/drive_upload.py) (`--target-mime application/vnd.google-apps.presentation`).

## Workflow

1. **Isolate scratch & verify auth**: run `umask 077; SCRATCH="$(mktemp -d)"` and execute `gws` from `"$SCRATCH"`. Check `gws auth status` without printing secrets and confirm folder/template IDs (`supportsAllDrives: true`).
1. **Build or patch (dry-run first)**: adapt [draft_slides.py](templates/draft_slides.py) or inspect `gws slides presentations batchUpdate --dry-run` before mutating. Keep `presentationId` in `--params` and `requests` in `--json` (set `writeControl.requiredRevisionId` when editing an existing deck).
1. **Verify visually & read back**: confirm slide count via `gws slides presentations get --params '{"presentationId":"<ID>","fields":"presentationId,title,slides(objectId)"}'`, export a PDF preview via `gws drive files export` (`mimeType: application/pdf`) or fetch slide thumbnails (`presentations.pages.getThumbnail`), inspect rendered frames visually, and run `fmind-review-visuals` plus the [humanize pre-send gate](../../../humanize/SKILL.md#pre-send-gate) (`fmind-review-human` for slide copy/insight; [subagent](../../../subagent/SKILL.md)).
1. **Hand off**: return `[<Title>](https://docs.google.com/presentation/d/<ID>/edit)` and never widen Drive sharing without explicit approval.

## Gotchas

- **No public URLs for `createImage`**: never make Drive images public just to call `createImage`; import via `.pptx` + `drive_upload.py` instead.
- **Units & IDs**: Slides API geometry uses EMU (`1 pt = 12700 EMU`; 16:9 slide is `9144000 x 5143500 EMU` = `720 x 405 pt`). Provide deterministic `objectId` values (5–50 chars `[a-zA-Z0-9_-]`) so follow-up style requests target the exact element.
- **Template ACLs**: `drive.files.copy` inherits destination `parents` ACLs; verify with `gws drive permissions list`.

## Documentation

- [Google Slides API](https://developers.google.com/workspace/slides/api/guides/presentations) · [Slides `batchUpdate`](https://developers.google.com/workspace/slides/api/guides/batch) · [Drive uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads) · Companions: [draft/typst-deck](../typst-deck/GUIDE.md), [humanize](../../../humanize/SKILL.md), [diagrams-as-code](../../../diagrams-as-code/SKILL.md), [gws](../../../gws/SKILL.md).
