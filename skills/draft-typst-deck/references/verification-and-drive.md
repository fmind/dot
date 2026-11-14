# Verification, Google Slides Compatibility, and Safe Upload

## 1. Compile, Font, Word-Cap, & Visual Gate

1. Always pass `--expected-slides <N>` (plus `--max-words 30` for Fmind-theme decks and `--pptx` when building `.pptx` / Google Slides) to [build_typst_deck.py](../scripts/build_typst_deck.py) `check`.
1. Standalone cards via `render` and deck figures (`--render-figures`) run the same strict warning checks (`unknown font family`, empty bold `*...*` warnings) and fail closed unless `--allow-font-warnings` is explicitly set. Theme fonts (`Google Sans`, `Google Sans Code`) are auto-discovered from `assets/fonts/`, `~/.local/share/fonts`, or `~/Library/Fonts`.
1. Inspect every rendered PNG frame before sharing: confirm open whitespace, unclipped chart labels, one focal visual, zero prose backticks, and scannable hierarchy.
1. Audit chart accuracy: equal comparison criteria, stated sample sizes on bars and headlines, conservative rounded ranges, and zero secrets or internal identifiers.

## 2. Google Slides Compatibility & Alternatives

Typst compiles to PDF, Retina PNG, SVG, and queryable metadata rather than native Slides shapes. Pick the workflow matching who edits next:

| Goal                                       | Recommended path                                                                                                            | Trade-off & security boundary                                                                 |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Pixel-perfect Typst deck in Slides**     | `check --pptx` -> `upload deck.pptx --google-slides --source-dir .`                                                         | Exact Fmind visuals + **editable speaker notes** in Slides; slide body is a sharp Retina PNG. |
| **Stakeholders edit on-slide text boxes**  | Adapt [editable_deck.py](../templates/editable_deck.py) (`Google Sans` shapes + Typst `figures/*.png`) -> `--google-slides` | Native editable Google Slides shapes/text (`Google Sans` works natively); simpler card grid.  |
| **Fill an existing client Slide template** | `gws slides presentations batchUpdate` (`replaceAllText` placeholders) after copying template                               | Preserves client master theme natively without rebuilding layout.                             |
| **Never do this**                          | `gws slides ... createImage` or unpinned `typ2pptx` / Marp                                                                  | `createImage` requires world-readable public image URLs; unpinned converters drift fonts.     |

## 3. Isolated `gws` Drive & Google Slides Upload

[gws](../../gws/SKILL.md) rejects `--upload` paths outside `cwd` and auto-loads `.env` in repos; `build_typst_deck.py upload` runs inside a fresh `tempfile.TemporaryDirectory`:

1. **Local integrity**: checks `%PDF-` header on `.pdf` or valid ZIP containing `ppt/presentation.xml` on `.pptx` (and extracts `<dc:title>` when naming native Google Slides).
1. **Remote targeting**: `--file-id <ID>` updates in place (preserving URL/revisions); `--drive-folder <ID>` matches existing non-trashed files of the same target `mimeType` across paginated listings (`--name` overrides filename).
1. **Optional source sync**: `--source-dir <dir>` mirrors `.typ`, `figures/*.typ`, and root `.py` deck scripts into `<folder>/assets/<deck-slug>/` in Drive.
1. **Verified read-back**:
   - **PDF / binary `.pptx`**: verifies remote `md5Checksum` + byte `size`.
   - **`--google-slides`**: verifies Drive `mimeType == application/vnd.google-apps.presentation`, `trashed == false`, and `gws slides presentations get` slide count matching local `.pptx`.
1. Check ACLs with `gws drive permissions list` and get explicit approval before widening sharing.
