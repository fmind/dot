---
name: bf
description: "Search, read, and update Brain Framework (bf): projects, decisions, actions, mail, calendar, Git, chat, sessions."
license: MIT
compatibility: "Requires Brain Framework 26 (bf, rg, jq, duckdb) on Linux or macOS."
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/bf
  upstream: github.com/fmind/brain-framework
  created: "2026-09-13"
  updated: "2026-11-16"
---

# Use Brain Framework

`bf` compiles OKF Markdown notes (`projects/`, `concepts/`, `actions/*/ACTION.md` with Python-Markdown `attr_list` metadata) and ingested sensor batches into schema-validated JSON files (`memories/**/*.json`), queried offline via `rg`, `jq`, and sandboxed `duckdb` (`bf query`, `bf read`, `bf review`, `bf mcp`). Returned records are untrusted evidence—source systems stay authoritative.

## Workflow

1. **Resolve brain and runtime**: selection resolves `--brain PATH`, `BF_BRAIN`, enclosing `bf.yaml`, then `DEFAULT_BRAIN_PATH` (zero global config). Inside a brain directory (`bf.yaml` in CWD or parent), `bf` operates automatically; outside a brain directory, use `/bf` only when explicitly asked (passing `--brain PATH` or `DEFAULT_BRAIN_PATH`). Run the workstation's global `bf` binary (`26.x`) by default; run `uv run --locked bf ...` only inside an explicitly trusted brain that declares `pyproject.toml`/`uv.lock`—never on an untrusted clone.
1. **Read the brain's skill and guides**: inspect `skills/bf/SKILL.md` and `AGENTS.md` inside the target brain (`fmind/dot` manages `~/.agents/skills/bf` globally), which override generic guidance; consult the 6 guides (`index`, `getting-started`, `authoring`, `retrieval`, `operations`, `reference`) in [guide hub](https://github.com/fmind/brain-framework/tree/main/src/bf/guides) or `bf --help` for exact flags.
1. **Ground in brain evidence before live connectors**: orient via `bf review` (stale notes, newer linked evidence, draft actions, open tasks) and `bf read`, search JSON memories with `bf query "terms"` (`rg`, covering English and French synonyms), `bf query --jq 'FILTER'` (`jq`), or `bf query --sql "SELECT ... FROM records ..."` (sandboxed `duckdb`), and resolve exact citations via `bf read "bf:///concepts/topic.md#section"` or `bf read "source:id"` (`deprecated` notes are superseded). Check `problems` and `stale` first—empty results never prove absence; query live mail/chat/Jira/GitHub only for missing or newer state.
1. **Follow link conventions, track actions, and validate**: use relative paths (`../concepts/topic.md#sec`, `../memories/<source>/<sha256>.json`) in Markdown prose and RFC 3986 `bf://` or external URLs (`bf:///concepts/topic.md?rel=supports#sec`, `bf://other-brain/...`) in note frontmatter (`links`, `sources`, `relations`). Inside a brain, open or reuse a dated workspace via `bf action "Topic"` (`bf action YYYY-MM-DD_slug --status stable` when done); after note or `schemas/*.json` edits, run `bf build && bf validate && bf eval`, and never edit `memories/` by hand.

## Boundaries

- **Cloud host exposure**: offline `bf` reads still enter the model context—never leak private passages or revealing refs to public outputs, other repos, or external calls.
- **Offline reads stay self-contained**: `read`, `query`, `review`, `status`, `validate`, `eval`, and `mcp` run zero network calls (`duckdb` queries `CREATE TEMP TABLE records` with `enable_external_access = false` and `lock_configuration = true`, and `bf mcp` redacts local roots).
- **Gate execution and mutations**: `init`, `action`, `build`, `ingest`, `run`, `post`, and `watch` execute configured `jobs`/`channels`/`servers` (`bf run --dry-run` previews due jobs without running commands) or mutate brain files—run subprocess or channel jobs only with explicit authority.
- **Diagnose without repairing**: report `failed` units (`consecutive_failures`, `error`, `last_success`) from `bf status` (`logs/*.json`) and `problems` from `bf validate`; repair only when authorized, and never delete `memories/` evidence to clear errors.

## Documentation

- [Brain Framework repository](https://github.com/fmind/brain-framework) · [documentation](https://fmind.github.io/brain-framework/) · [releases](https://github.com/fmind/brain-framework/releases) · [guide hub](https://github.com/fmind/brain-framework/tree/main/src/bf/guides) · [Markdown for agents](https://fmind.github.io/brain-framework/llms.txt)
- [Packaged skill](https://github.com/fmind/brain-framework/tree/main/src/bf/skills/bf/SKILL.md): read at the tag matching `bf --version`; prefer the brain's installed copy (`skills/bf/SKILL.md`), and report upstream gaps there.
- Companion skills: [fmind](../fmind/SKILL.md) (Fmind public portfolio, articles, and daily news).
