# Verification and Safe Drive Upload

## 1. Compile, Font, Word-Cap, & Visual Gate

1. Always pass `--expected-slides <N>` (plus `--max-words 30` on standard slides, or up to `--max-words 45` on data-dense comparative charts, and `--pptx` when exporting `.pptx`) to [build_typst_deck.py](../scripts/build_typst_deck.py) `check`.
1. Standalone cards via `render` and deck figures (`--render-figures`) fail closed on `unknown font family` and empty `*...*` warnings unless `--allow-font-warnings` is explicitly set. Theme fonts (`Google Sans`, `Google Sans Code`) are auto-discovered from `assets/fonts/`, `~/.local/share/fonts`, or `~/Library/Fonts`.
1. Visually inspect every rendered `_preview/<stem>-*.png` frame before sharing: confirm open whitespace, unclipped labels, one focal visual, and scannable hierarchy.
1. Fan out `fmind-review-visuals` + `fmind-review-human` per [humanize](../../../../humanize/SKILL.md#pre-send-gate) (add `fmind-review-factcheck` when needed) before publishing.

## 2. Google Slides Compatibility

| Goal                                   | Recommended path                                                                                                                        | Trade-off                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Pixel-perfect Typst deck in Slides** | `check --pptx` -> [`drive_upload.py`](../../../../gws/scripts/drive_upload.py) `--target-mime application/vnd.google-apps.presentation` | Exact Typst visuals + editable speaker notes; slide body is a Retina PNG.  |
| **Native editable Google Slides**      | Use [draft/slides](../../slides/GUIDE.md)                                                                                               | Editable text/shapes via `gws slides` or client template `replaceAllText`. |
| **Standalone PDF or PPTX**             | `drive_upload.py deck.pdf --drive-folder <ID>`                                                                                          | Exact binary verified by remote `md5Checksum` + `size`.                    |

## 3. Safe Upload via `drive_upload.py`

[`drive_upload.py`](../../../../gws/scripts/drive_upload.py) isolates `gws` inside a fresh `tempfile.TemporaryDirectory` (avoiding ancestor `.env` files), validates Drive IDs/names, upserts by `--drive-folder` + name or updates `--file-id` in place, and verifies read-back (`trashed == false`, `mimeType`, and `md5Checksum`/`size` for binary uploads). Check ACLs with `gws drive permissions list` and ask before widening sharing.

## Documentation

- [Google Slides API](https://developers.google.com/workspace/slides/api/guides/presentations) · [Drive upload guide](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
