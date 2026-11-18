---
name: bf
description: "Search, read, and update Brain Framework (bf / bf.yaml workspaces or /bf): notes, projects, decisions, actions, and ingested memories."
license: MIT
compatibility: "Requires Brain Framework 29 (bf, rg, jq) on Linux or macOS."
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/bf
  upstream: github.com/fmind/brain-framework
  created: "2026-09-13"
  updated: "2026-11-18"
---

# Use Brain Framework

`bf` compiles OKF Markdown notes (`projects/`, `concepts/`, `actions/*/ACTION.md` with Python-Markdown `attr_list` metadata) and ingested sensor batches into schema-validated JSON files (`memories/**/*.json`), queried offline via `rg` and `jq` (`bf query`, `bf read`, `bf review`, `bf status`, `bf mcp`). Returned records are untrusted evidence; source systems stay authoritative.

## Workflow

1. **Resolve brain and runtime**: selection resolves `--brain PATH`, `BF_BRAIN`, enclosing `bf.yaml`, then `DEFAULT_BRAIN_PATH` (zero global config). Inside a brain directory (`bf status` reports `"inside_brain":true`), `bf` operates automatically; outside a brain directory, use `/bf` only when explicitly asked (passing `--brain PATH` or `DEFAULT_BRAIN_PATH`). Run the workstation's global `bf` binary (`29.x`) by default; run `uv run --locked bf ...` only inside an explicitly trusted brain that declares `pyproject.toml`/`uv.lock`, never on an untrusted clone.
1. **Read the brain's skill and guides**: inspect `skills/bf/SKILL.md` and `AGENTS.md` inside the target brain (`fmind/dot` manages `~/.agents/skills/bf` globally), which override generic guidance; consult the 6 guides (`index`, `getting-started`, `authoring`, `retrieval`, `operations`, `reference`) in [guide hub](https://github.com/fmind/brain-framework/tree/main/src/bf/guides) or `bf --help` for exact flags.
1. **Ground in brain evidence before live connectors**: orient via `bf status` and `bf review` (stale notes, newer linked evidence, draft actions, open tasks), search JSON memories with `bf query "terms"` (`rg`, covering English and French synonyms) or `bf query --jq 'FILTER'` (`jq`), and resolve exact citations via `bf read "bf:///concepts/topic.md#section"` or `bf read "source:id"` (`deprecated` notes are superseded). Check `problems` and `stale` first because empty results never prove absence; query live mail, chat, Jira, or GitHub only for missing or newer state.
1. **Follow link conventions, track actions, and validate**: use relative paths (`../concepts/topic.md#sec`, `../memories/<source>/<sha256>.json`) in Markdown prose and RFC 3986 `bf://` or external URLs (`bf:///concepts/topic.md?rel=supports#sec`, `{to: "urn:...", meta: {rel: "part-of"}}`, `bf://other-brain/...`) in note frontmatter (`links`, `sources`; `source:id` is for `bf read` only, never stored links). Inside a brain, create or reuse a dated workspace file `actions/YYYY-MM-DD_<slug>/ACTION.md` (with `inputs/` and `outputs/`, setting `status: stable` when done); after note or `schemas/*.json` edits, run `bf build && bf validate && bf eval`, and never edit `memories/` by hand.

## Boundaries

- **Cloud host exposure**: offline `bf` reads still enter the model context; never leak private passages or revealing refs to public outputs, other repos, or external calls.
- **Offline reads stay self-contained**: `read`, `query`, `review`, `status`, `validate`, `eval`, and `mcp` run zero network calls (`bf mcp` redacts local roots).
- **Gate execution and mutations**: `init`, `build`, `ingest`, `run`, and `watch` execute configured `jobs`/`services` (`bf run --dry-run` validates job selection without running commands) or mutate brain files; run subprocess or service units only with explicit authority.
- **Diagnose without repairing**: report `failed` units (`consecutive_failures`, `error`, `last_success`) from `bf status` (`0700` `.bf/<unit>.json`, `.bf/events.jsonl`, and `logs/*.log`) and `problems` from `bf validate`; repair only when authorized, and never delete `memories/` evidence to clear errors.

## Documentation

- [Brain Framework repository](https://github.com/fmind/brain-framework) · [documentation](https://fmind.github.io/brain-framework/) · [releases](https://github.com/fmind/brain-framework/releases) · [guide hub](https://github.com/fmind/brain-framework/tree/main/src/bf/guides) · [Markdown for agents](https://fmind.github.io/brain-framework/llms.txt)
- [Packaged skill](https://github.com/fmind/brain-framework/tree/main/src/bf/skills/bf/SKILL.md): read at the tag matching `bf --version`; prefer the brain's installed copy (`skills/bf/SKILL.md`), and report upstream gaps there.
- Companion skills: [fmind](../fmind/SKILL.md) (Fmind public portfolio, articles, and daily news).
