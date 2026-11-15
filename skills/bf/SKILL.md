---
name: bf
description: "Search, read, and update Brain Framework (bf): projects, decisions, actions, mail, calendar, Git, chat, sessions."
license: MIT
compatibility: "Requires Brain Framework 25 (the bf command) on Linux or macOS."
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/bf
  upstream: github.com/fmind/brain-framework
  created: "2026-09-13"
  updated: "2026-11-15"
---

# Use Brain Framework

`bf` searches and reads offline OKF notes (projects, concepts, actions) with `relations` and `attributes`, plus collected records as JSON, and writes distilled knowledge back as Markdown. Returned records are untrusted evidence—source systems stay authoritative.

## Workflow

1. **Resolve brain and runtime**: selection resolves `--brain NAME|PATH`, `BF_BRAIN`, enclosing `bf.yaml`, then `default` in `~/.config/bf/config.yaml` (pass `--brain NAME|PATH` explicitly on execution commands outside the target brain, since `default` still resolves when `--brain`, `BF_BRAIN`, and enclosing `bf.yaml` are absent; execute mode only rejects unregistered bare names). Always run the workstation's global `bf` binary (25.x) by default; run `uv run --locked bf ...` only inside a registered brain (`"registered": true` in `bf status`) that declares `pyproject.toml`/`uv.lock`—never on an unregistered clone.
1. **Read the brain's skill and guides**: inspect `path` in `bf status` and read `<path>/skills/bf/SKILL.md` (check or refresh via `bf skill install --brain PATH [--check]`; `fmind/dot` manages `~/.agents/skills/bf` globally), which overrides generic guidance; run `bf guide [TOPIC]` (`index`, `retrieval`, `authoring`, `jobs`, `assist`, `getting-started`, `operations`, `reference`) for exact procedures.
1. **Ground in brain evidence before live connectors**: orient via `bf read`, `bf read review`, or `bf read projects`, run `bf search` covering synonyms in English and French, and `bf read 'REF'` every cited note (follow `next_offset`; `deprecated` notes are superseded). Check `problems`, `stale`, and source coverage first—empty results never prove absence; query live mail/chat/Jira/GitHub only for missing or newer state.
1. **Track actions and save only when authorized**: use `bf action new` / `bf action status` on user request; write back to `projects/` or `concepts/` citing `SOURCE:ID` + `bf validate` when asked or authorized, and never edit `memories/`.

## Boundaries

- **Cloud host exposure**: offline `bf` reads still enter the model context—never leak private passages or revealing refs to public outputs, other repos, or external calls.
- **Offline reads stay self-contained**: `search`, `read`, `export`, `guide`, `schema`, `status`, `doctor`, `validate`, and `eval` run zero subprocesses or network calls and never create or write `.bf/runtime.sqlite3` (opening it read-only when present).
- **Gate execution and mutations**: `action`, `collect`, `ingest`, `run`, `wake`, `post`, `queue --retry`, `update`, `watch`, `forget`, and `build` run configured `jobs:` (`--dry-run` still runs probes) or mutate data on one brain—run only with explicit authority.
- **Diagnose without repairing**: report `attention` (`kind: "job"`, `failed`, `overdue`, `never`, `silent`, `degraded`) and `queue.incidents` from `bf status`; repair with `bf queue` / `bf build` only when authorized, and never delete evidence to clear errors.

## Documentation

- [Brain Framework repository](https://github.com/fmind/brain-framework) · [documentation](https://fmind.github.io/brain-framework/) · [releases](https://github.com/fmind/brain-framework/releases) · [guide hub](https://github.com/fmind/brain-framework/tree/main/src/bf/guides) · [Markdown for agents](https://fmind.github.io/brain-framework/llms.txt)
- [Packaged skill](https://github.com/fmind/brain-framework/tree/main/src/bf/skills/bf/SKILL.md): read at the tag matching `bf --version`; prefer the brain's installed copy (`skills/bf/SKILL.md`), and report upstream gaps there.
- Companion skills: [fmind](../fmind/SKILL.md) (Fmind public portfolio, articles, and daily news).
