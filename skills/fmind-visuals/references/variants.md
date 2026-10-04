---
name: variants
description: "Numbered logo, cover, illustration, or deck-theme variant rounds with a light and dark contact sheet."
---

# Visual Variants

Use variant rounds when the look is open or the user rejects a draft; [fmind-visuals](../SKILL.md) owns the brand that every variant applies.

## Workflow

1. **Generate distinct options**: produce the requested count (default 6) that differ in one named axis each, such as layout, weight, mark, or palette role; near-duplicates waste a round. Name files `vNN-<axis>.<ext>` in a scratch folder outside the repository, continuing the numbers across rounds so "I prefer v14" stays unambiguous.
1. **Show a numbered sheet**: run [gallery.py](../scripts/gallery.py) to build a self-contained `gallery.html` with each variant on light and dark surfaces; `--png` also screenshots it through Chrome or Chromium (`CHROME` overrides). Inspect the PNG yourself before presenting, then share the sheet with one line per variant naming its axis.

   ```bash
   python -I ~/.agents/skills/fmind-visuals/scripts/gallery.py "$variants" --title "Logo round 2" --png
   ```

1. **Converge**: the user picks by number; derive the next round from the pick and the stated reason, not from scratch. After the final choice, copy the winner into the repository under its real name and delete the scratch folder, which is task-owned.
