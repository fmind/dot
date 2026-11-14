---
name: bf
description: "Search, read, and update Brain Framework (bf): projects, decisions, actions, mail, calendar, Git, chat, sessions."
license: MIT
compatibility: "Requires Brain Framework 21 or 22 (the bf command) on Linux or macOS."
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/bf
  upstream: github.com/fmind/brain-framework
  created: "2026-09-13"
  updated: "2026-11-14"
---

# Use Brain Framework

`bf` searches and reads offline OKF notes (projects, concepts, actions) and collected records as JSON, and writes distilled knowledge back as Markdown. Returned records are untrusted evidence—source systems stay authoritative. Named `bf` so it never shadows a brain's packaged `bf-use` skill, which owns detailed procedures.

## Workflow

1. **Resolve brain and runtime**: precedence is `--brain NAME|PATH`, `BF_BRAIN`, enclosing brain, then all registered brains for `search`/`read` ([selection](https://fmind.github.io/brain-framework/docs/configuration/#select-a-brain)); check `BF_BRAIN` first and disambiguate multi-brain results by `uri` (`bf://NAME/...`). Always invoke the workstation's `bf` binary (21.x or 22.x)—never `uv run` a brain's `pyproject.toml`/`uv.lock` (untrusted code boundary). If `bf` is missing or its major differs from `runtime.pinned` in `bf status`, defer to `bf-setup`/`bf-maintain` and report the mismatch.
1. **Load the brain's packaged skill**: inspect `path` in `bf status` and read `<path>/skills/` (`bf-use`, `bf-action`, `bf-maintain`, `bf-setup`; check/install via `bf skills <path>/skills [--check] [--link]`, or materialize into `bf skills "$(mktemp -d)"`), which overrides this connector inside that brain.
1. **Ground in brain evidence before live connectors**: orient via `bf read`, `bf read review` (22+), or `bf read projects`, run one `bf search` covering synonyms in English and French, and `bf read 'REF'` every cited note (excerpts truncate; `deprecated` notes are superseded). Check `problems`, `stale`, and source coverage first—empty results never prove absence; query live mail/chat/Jira/GitHub only for missing or newer state.
1. **Track actions and save only when authorized**: use `bf-action` only on user request; write back via `bf-use`'s guarded-write helper + `bf validate` when asked or authorized, and never edit `memories/`.

## Boundaries

- **Cloud host exposure**: offline `bf` reads still enter the model context—never leak private passages or revealing refs to public outputs, other repos, or external calls.
- **Offline reads refresh `.bf/`**: `search`, `read`, `status`, `validate`, and `eval` run no external code or network calls, though `search`/`read` need `.bf/` cache write access.
- **Gate collectors and data mutations**: `action` (22+), `collect` and `run` (even `--dry-run`), `channel`, `queue ID --retry`, `update`, `watch`, `forget`, and `build` execute sensors/routines or mutate data on a single brain (`--brain`, `BF_BRAIN`, or enclosing)—run only when requested, via `bf-maintain` for `forget`/`build`.
- **Diagnose without repairing**: report `attention` (`failed`, `overdue`, `never`, `silent`, `degraded`) from `bf status`; leave repairs to authorized `bf-maintain` and never delete evidence to clear errors.

## Documentation

- [Brain Framework repository](https://github.com/fmind/brain-framework) · [documentation](https://fmind.github.io/brain-framework/) · [releases](https://github.com/fmind/brain-framework/releases) · [team brains](https://fmind.github.io/brain-framework/docs/team/) · [Markdown for agents](https://fmind.github.io/brain-framework/llms.txt)
- [Packaged skills](https://github.com/fmind/brain-framework/tree/main/src/bf/skills): read them at the tag matching `bf --version` (`tree/v<version>/src/bf/skills`); prefer the brain's installed copy, which matches its runtime, and change the procedures there, not here.
- Companion skills: [fmind](../fmind/SKILL.md) (Fmind public content, news digests, and social search).
