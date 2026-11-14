# Evaluation, Catalog Review, and Adoption Probing

Use data and isolated behavioral probes together before adding, merging, or pruning skills.

## 1. Measure Real Catalog Usage

Run the local transcript counter ([skill_loads.py](../scripts/skill_loads.py)) across agy, Claude Code, and Pi sessions (reads only paths and timestamps; ignores prompt content and excludes bulk catalog-review sessions):

```bash
python3 -I ~/.agents/skills/skillify/scripts/skill_loads.py --days 30 --json
```

Check text output too: recently created skills within the window with zero observed loads are annotated `name(new:YYYY-MM-DD)` so new capabilities are not mistakenly pruned as unused.

Run startup token budget checks on every catalog edit:

```bash
dot agent context --source . --project . --details --check
```

## 2. Decide Whether to Trim, Merge, or Retire

- **High-load core tasks (`humanize`, `python-stack`, `full-review`)**: trim model-known basics aggressively, tighten visual/security defaults, and ensure examples match current tool versions.
- **Zero-load mature skills (`>30` days since creation)**: inspect discovery description, missing triggers, or overlap with a neighboring owner (`package-rules.md`). Merge thin siblings or demote to `.agents/skills/` or a plain `references/` note instead of keeping unused global discovery overhead.
- **Overloaded collections (`SKILL.md` >100 lines)**: keep routing tables crisp and move deep edge cases into `references/`.

## 3. Probe Adoption and Trigger Fit

Exercise non-trivial additions, splits, or routing changes in an isolated scratch workspace rather than trusting prose inspection alone:

1. **Direct trigger**: prompt that matches `description` wording naturally — verify the intended skill loads and its procedure/script runs end to end.
1. **Neighbor disambiguation**: prompt near an adjacent owner (for example `draft-typst-deck` vs `diagrams-as-code`, or `repository-docs` vs `humanize`) — verify the right owner wins.
1. **Negative control**: generic task requiring no specialized skill — verify false loads stay zero.

On large catalog overhauls, run `12–20` probes spanning explicit, implicit, neighbor, and no-skill cases, verify on real binaries (`typst`, `pytest`, `uv`) where available, and report any unavailable host checks separately.
