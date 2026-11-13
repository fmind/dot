# Verification, Honesty Audit, and Safe Drive Upload

## 1. Compile, Font & Overflow Gate

1. Always pass `--expected-slides <N>` matching your outline to [build_typst_deck.py](../scripts/build_typst_deck.py) `check`. Typst spills silently onto extra pages when a list or panel exceeds `540pt`; `--expected-slides` fails immediately on any mismatch.
1. Keep theme fonts (`Google Sans`, `Google Sans Code`) reachable via `--font-path`, `assets/fonts/`, `~/.local/share/fonts`, or `~/Library/Fonts`. `check` treats `unknown font family` warnings as failures by default (`--allow-font-warnings` opts out only for explicit fallback testing).
1. Visually inspect every rendered PNG (`_preview/<stem>-1.png` .. `<stem>-N.png`) before sharing:
   - Confirm clean margins and footer spacing (no text overlapping card borders or page numbers).
   - Confirm zero wrapped metric values or clipped labels inside `bar-panel` rows and `step-card` boxes.
   - Confirm each slide carries one takeaway and scans comfortably at normal zoom in under 15 seconds.

## 2. Pre-Share Honesty & Comparison Audit

Before sharing an executive or benchmark deck externally, check every slide and visual against primary evidence:

1. **Verified vs partial checks**: distinguish syntax/build verification from live integration or runtime execution. Never imply full end-to-end verification when only partial checks ran.
1. **Proposed vs adopted outcomes**: distinguish open/draft deliverables from merged, approved, or adopted production changes, noting pending metrics explicitly.
1. **Apples-to-apples chart units**: when compared tools report different granularities (for example raw occurrences vs deduplicated units), state the unit difference directly in the panel `subtitle` or callout.
1. **Sub-cohort attribution**: when a baseline only ran on a subset (`45` of `83` workloads), put the exact sample size on both the bar annotation and the slide takeaway.
1. **Symmetrical scope breakdown**: if mitigations or exclusions (`edge`, `allowlist`) are separated on one option, apply the same split to every compared option.
1. **Privacy & data classification**: keep internal tokens, customer identifiers, credentials, and hostnames out of public or untrusted shares.

## 3. Isolated `gws` Drive PDF Upload

[gws](../../gws/SKILL.md) rejects `--upload` paths outside the current working directory and auto-loads `.env` if launched inside a repository. `build_typst_deck.py upload` isolates every API call:

1. Validates `%PDF-` header bytes and non-zero size locally before touching Drive.
1. Runs every `gws` call inside a single fresh `tempfile.TemporaryDirectory` (`cwd=tmp_dir`), staging the PDF by plain filename for `--upload`.
1. Uses `--file-id "<FILE_ID>"` to update an existing PDF in place (preserving URL, viewers, and revision history, keeping its existing Drive name unless `--name` is given) or `--drive-folder "<FOLDER_ID>"` to create/upsert by filename across paginated folder listings.
1. Optionally applies `copyRequiresWriterPermission: true` when `--protect-copy` is passed, and verifies remote `md5Checksum` + `size` parity via `drive.files.get` read-back.
1. Run `gws drive permissions list --params '{"fileId": "<FILE_ID>", "supportsAllDrives": true}'` and get explicit confirmation before widening Drive sharing permissions.
