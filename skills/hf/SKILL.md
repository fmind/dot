---
name: hf
description: "Operate Hugging Face models, datasets, Spaces, and jobs with hf."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/hf
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Hugging Face CLI

Operate Hugging Face Hub with `hf` (`pypi:huggingface_hub`): auth, bounded transfers, cache hygiene, and authority gates on uploads and paid compute. Non-workstation hosts should set `HF_HUB_DISABLE_TELEMETRY=1` and `HF_HUB_DISABLE_UPDATE_CHECK=1`.

## Workflow

1. **Verify account**: `hf auth whoami` (`hf auth login` or env `HF_TOKEN`; never run `hf auth token`).
1. **Inspect before downloading**: use `hf models|datasets|spaces info|card|ls --limit 10`, or query remote Parquet in place with `hf datasets sql`.
1. **Download into gitignored paths** (gated repos require prior web license acceptance):

   ```bash
   hf download <repo-id> --local-dir models/<name>
   hf download <owner>/<dataset> --repo-type dataset --local-dir data/<name>
   ```

1. **Clean only task-owned cache** (`HF_HOME` relocates future caches): inspect `hf cache ls`, preview `hf cache prune --dry-run` / `hf cache rm <repo-or-rev> --dry-run`, then pass `--yes`—broad pruning requires explicit approval.
1. **Upload privately with authority**: confirm repo, visibility, and license first. Always pass `--private` on `repos create`, `upload`, and `buckets create` (missing targets inherit org/account public defaults), preview `hf sync --dry-run` (`--delete` needs explicit approval), and verify via `hf models info` or `hf repos ls`.
1. **Gate paid compute and public ports**: preview `hf jobs [uv] run --dry-run` before billing, pass secrets by name (`--secrets HF_TOKEN`, never `NAME=value`), never pass unauthenticated `--expose-public` unapproved, apply the same spend gate to `hf sandbox` and hourly `hf endpoints deploy`, and tear down with `hf jobs cancel`, `hf sandbox kill`, or `hf endpoints pause`.

## Gotchas

- **Use `hf`, never legacy `huggingface-cli`**.
- **Size and verify transfers**: run `dot doctor --headroom` first, filter with `--include`/`--exclude`, preview sizes via `hf download <repo-id> --dry-run`, pin `--revision <sha>` (auditing any `trust_remote_code`), and verify local bytes via `hf cache verify <repo-id> --revision <sha>` (`--local-dir`, `--fail-on-missing-files`).
- **Always pass `--dest` to `hf skills add`**: omitting `--dest` symlinks into `.claude/skills` (2.3.0+ skips only when `.claude/skills` already resolves to `.agents/skills`).

## Official Skills

Upstream: `huggingface/skills`—audit immutable snapshots per [vendor-skill policy](../agent-project/references/vendor-skills.md) instead of unpinned `hf skills add <name>`. Only install version-matched `hf-cli` via `hf skills preview` and `hf skills add --dest .agents/skills` (or `hf skills update hf-cli --dest .agents/skills`).

## Documentation

- [hf CLI guide](https://huggingface.co/docs/huggingface_hub/en/guides/cli) · [huggingface/skills](https://github.com/huggingface/skills)
- Releases: [huggingface_hub](https://github.com/huggingface/huggingface_hub/releases)
- Companion skills: [kaggle](../kaggle/SKILL.md), [colab](../colab/SKILL.md), [python-stack](../python-stack/references/foundation/GUIDE.md).
