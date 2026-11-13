# Verification, Google Slides Alternatives, and Safe Upload

## 1. Compile, Font, Overflow, & Visual Gate

1. Always pass `--expected-slides <N>` (and `--pptx` when building a `.pptx` / Google Slides deck) to [build_typst_deck.py](../scripts/build_typst_deck.py) `check`. Any content spill changes page count and fails immediately.
1. Theme fonts (`Google Sans`, `Google Sans Code`) are auto-discovered from `assets/fonts/`, `~/.local/share/fonts`, or `~/Library/Fonts`; missing-font warnings fail closed (`--allow-font-warnings` opts out explicitly).
1. Inspect every `_preview/<stem>-*.png` frame before sharing: confirm generous margins, zero clipped chart labels, ≤30 on-slide words, zero prose backticks, and one scannable takeaway per slide.
1. Audit chart accuracy: equal comparison criteria, stated sample sizes on bars and headlines, conservative rounded ranges, and zero secrets or internal identifiers.

## 2. Google Slides Compatibility & Alternatives

Typst outputs PDF, PNG, SVG, and queryable JSON metadata — never native editable Google Slides objects directly:

| Goal                                       | Recommended path                                                                                                               | Trade-off & security boundary                                                                   |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **Pixel-perfect Typst deck in Slides URL** | `check --pptx` → `upload deck.pptx --google-slides --source-dir .`                                                             | Preserves exact Fmind visuals + **editable speaker notes** cleanly; slide canvas is Retina PNG. |
| **Stakeholders edit slide text directly**  | Build `.pptx` with `uv run --with python-pptx` (`Google Sans` native boxes + Typst `figures/*.png`) → `upload --google-slides` | Text/tables stay editable in Slides; slightly looser layout fidelity than pure Typst.           |
| **Never do this**                          | `gws slides ... createImage` or unpinned `typ2pptx`                                                                            | `createImage` requires public world-readable image URLs; `typ2pptx` is unpinned/experimental.   |

## 3. Isolated `gws` Drive & Google Slides Upload

[gws](../../gws/SKILL.md) rejects `--upload` paths outside `cwd` and auto-loads `.env` in repos; `build_typst_deck.py upload` runs inside a fresh `tempfile.TemporaryDirectory`:

1. **Local integrity**: checks `%PDF-` header on `.pdf` or valid ZIP containing `ppt/presentation.xml` on `.pptx`.
1. **Remote targeting**: `--file-id <ID>` updates in place (keeping URL/revisions); `--drive-folder <ID>` matches existing non-trashed files of the same target `mimeType` across paginated listings (`--name` overrides filename; `--google-slides` defaults to extensionless deck title).
1. **Optional editable source sync**: `--source-dir <dir>` mirrors `.typ` and `figures/*.typ` into `<folder>/assets/<deck-slug>/` in Drive.
1. **Verified read-back**:
   - **PDF / binary `.pptx`**: verifies remote `md5Checksum` + byte `size`.
   - **`--google-slides`**: verifies Drive `mimeType == application/vnd.google-apps.presentation`, `trashed == false`, and `gws slides presentations get` slide count matching local `.pptx`.
1. Check ACLs with `gws drive permissions list` and get explicit approval before widening sharing.
