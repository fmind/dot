---
name: hf
description: "Operate Hugging Face models, datasets, Spaces, and jobs with hf."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/hf
  created: "2026-09-16"
  updated: "2026-10-05"
---

# Hugging Face CLI

Use `hf` for Hub operations from the shell. The CLI generates its own command skill from the installed version; this skill owns authentication, cache hygiene, and the authority boundary around uploads and paid jobs.

## Workflow

1. **Resolve the account**: `hf auth whoami`; log in with `hf auth login` or pass `HF_TOKEN` through the environment. Never run `hf auth token` in a transcript or log.
1. **Read before writing**: `hf models info <repo-id>`, `hf models card <repo-id>`, `hf models ls --sort downloads --limit 10`, and the `datasets` and `spaces` twins answer most questions without a download.
1. **Download into an ignored directory**: gated repositories need the license accepted on the website first.

   ```bash
   hf download <repo-id> --local-dir models/<name>
   hf download <owner>/<dataset> --repo-type dataset --local-dir data/<name>
   ```

1. **Inspect cache use before cleanup**: `hf cache ls` and `hf cache prune --dry-run` show retained data and proposed deletions. Remove only recorded task-owned disposable entries with `hf cache rm <repo-id-or-revision>` after checking consumers; broad pruning of shared revisions or incomplete downloads requires explicit cleanup scope. `HF_HOME` relocates the cache for future operations.
1. **Upload with authority**: `hf repos create <repo-id> --private` then `hf upload <repo-id> <local-path> --private`; `hf upload` creates a missing repository with the account's default visibility unless `--private` is set. Confirm repository, visibility, and license before the first push, then verify with `hf models info` or `hf repos ls`.
1. **Run remote compute with authority**: `hf jobs run` and `hf jobs uv run` bill by hardware flavor; confirm the flavor and timeout, then watch `hf jobs logs` and `hf jobs ps`. `hf sandbox` VMs run on Jobs and `hf endpoints deploy` creates hourly-billed Inference Endpoints, so they need the same authority; release what you started with `hf sandbox kill` or `hf endpoints pause`.

## Gotchas

- **Use `hf`, not `huggingface-cli`**: `hf` replaced `huggingface-cli`; the mise tool is `pipx:huggingface_hub`.
- **Size large transfers before downloading**: inspect file selection and disk headroom before a download; use `--include`/`--exclude` when only part of a repository is needed, and `hf download <repo-id> --dry-run` to list the files, sizes, and total without downloading. Verify a downloaded revision with `hf cache verify <repo-id> --revision <sha>` (and `--local-dir` when used); add `--fail-on-missing-files` only when the complete revision was intended. This verifies downloaded bytes, not remote upload completion.
- **Pin a revision**: pass `--revision <sha>` for reproducible downloads; anything loaded with `trust_remote_code` is third-party code to review first.
- **Pass `--dest` to `hf skills add`**: without `--dest`, `hf skills add` also links each skill into `.claude/skills` (`~/.claude/skills` with `--global`). Where that directory already links to `.agents/skills`, as on this workstation, the command fails after installing, and `--force` deletes the skill and leaves a self-referencing link. Pass `--dest`, and never use `--force` while `.claude/skills` links to `.agents/skills`.

## Official Skills

Upstream: `huggingface/skills`, the same packages the CLI marketplace serves. The `hf`-native commands below replace the default installer while preserving the review and project-scope rules in the shared [vendor-skill policy](../agent-project/references/vendor-skills.md):

```bash
hf skills list
hf skills preview                            # review the generated CLI skill
hf skills add --dest .agents/skills          # the CLI skill
hf skills add <name> --dest .agents/skills
hf skills update
```

## Documentation

- [hf CLI guide](https://huggingface.co/docs/huggingface_hub/en/guides/cli) · [huggingface/skills](https://github.com/huggingface/skills)
- Releases: [huggingface_hub](https://github.com/huggingface/huggingface_hub/releases)
- Companion skills: [kaggle](../kaggle/SKILL.md), [colab](../colab/SKILL.md), [python-stack](../python-stack/references/foundation/GUIDE.md).
