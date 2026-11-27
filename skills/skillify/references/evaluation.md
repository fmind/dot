# Evaluation, Catalog Review, and Adoption Probing

Use data and isolated behavioral probes together before adding, merging, or pruning skills.

## 1. Measure Real Catalog Usage

Run the local transcript counter ([skill_loads.py](../scripts/skill_loads.py)) across local `agy` sessions (reads only paths and timestamps; ignores prompt content and excludes bulk catalog-review sessions):

```bash
python3 -I ~/.agents/skills/skillify/scripts/skill_loads.py --days 30 --json
```

- **New-skill annotation**: `--json` sets `"created"` (`YYYY-MM-DD` or `null`) and `"is_new"` (`true`/`false`) per skill entry (text mode appends `name(new:YYYY-MM-DD)` to unloaded recent skills) so newly created skills are not pruned as unused.
- **Measurement limits**: path matching also counts repo-editing reads under `skills/<name>/...` in a dotfiles checkout (not only `~/.agents/skills/`), and only local `agy` transcripts are scanned (Copilot CLI sessions are a blind spot).

Run startup token budget checks on every catalog edit:

```bash
dot context --source . --project . --details --check
```

## 2. Decide Whether to Trim, Merge, or Retire

- **Top-quartile loaded skills**: trim model-known basics aggressively, tighten visual/security defaults, and ensure examples match current tool versions.
- **Zero-load mature skills (`>30` days since creation)**: inspect discovery description, missing triggers, or overlap with a neighboring owner ([package-rules.md](package-rules.md)). Merge thin siblings or demote to `.agents/skills/` or a plain `references/` note instead of keeping unused global discovery overhead.
- **Over-budget skills**: keep collection routers within `~200–500` tokens excluding the generated guide index (`< 1,000` total), procedures `< 1,200` tokens, and every non-template Markdown file strictly `< 1,500` tokens by moving deep edge cases into `references/`.

## 3. Probe Adoption and Trigger Fit

Exercise non-trivial additions, splits, or routing changes in an isolated scratch workspace rather than trusting prose inspection alone:

1. **Direct trigger**: prompt that matches `description` wording naturally — verify the intended skill loads and its procedure/script runs end to end.
1. **Neighbor disambiguation**: prompt near an adjacent owner (for example `draft` vs `diagrams-as-code`, or `docs` vs `humanize`) — verify the right owner wins.
1. **Negative control**: generic task requiring no specialized skill — verify false loads stay zero.

Optionally on major catalog overhauls (or on request), expand to `12–20` probes spanning explicit, implicit, neighbor, and no-skill cases, verify on real binaries (`typst`, `pytest`, `uv`) where available, and report any unavailable host checks separately.
