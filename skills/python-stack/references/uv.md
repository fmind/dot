---
name: uv
description: "Dependency resolution, environments, packaging, and lockfiles."
---

# uv

Python dependencies, environments, builds, and lockfiles; [foundation](foundation/GUIDE.md) owns project defaults and [python-script](python-script/GUIDE.md) owns PEP 723 scripts.

## Workflow

1. **Add & sync**: add packages via `UV_MALWARE_CHECK=1 uv add --preview-features malware-check <pkg>` (blocks published OSV malware advisories pre-install, though sdist resolution still runs first; do not export globally) and reproduce envs via `uv sync --locked`.
1. **Verify lock**: run `uv lock --check` plus project gates after dependency edits.
1. **Out-of-tree wheel qualification**: export hashed deps (`uv export --locked --no-dev --no-emit-project -o requirements.txt` — skip when `dependencies = []`, as `uv` warns on empty files), then `uv venv`, `uv pip sync --require-hashes requirements.txt`, and `uv pip install <wheel>`.

## Gotchas

- **Reuse `mise` Python & shared cache**: align `.python-version` with `requires-python` per [tool-versions](../../mise/references/tool-versions.md#workstation-and-projects) and share `uv`'s hardlink/reflink [cache](https://docs.astral.sh/uv/concepts/cache/). Delete temporary qualification venvs/exports in `finally`, keep project `.venv`, and use `uv cache prune` only for periodic maintenance.
- **Inspect without importing**: run `uv pip show <dist>` and read `.venv/` files rather than importing untrusted/heavy modules.
- **Bound `uv_build` & commit `uv.lock`** (libraries included): keep `uv_build` within the `uv` release's [backend contract](https://docs.astral.sh/uv/concepts/build-backend/). Never use bare `uv run` or `uv sync` in gates (rewrites `uv.lock`); use `--locked` or `--frozen` (`UV_LOCKED`/`UV_FROZEN`).
- **Scrub `UV_*` when testing nested/separate repos**: inherited `UV_PROJECT`/`UV_*` redirect discovery (`VIRTUAL_ENV` targets `uv pip` only); unset them instead of passing `--no-config` (which drops `[tool.uv]` `required-version` and `python-preference`). Note: misspelled `[tool.uv]` keys only warn.
- **Triage `uv audit` findings**: upgrade first (`uv lock --upgrade-package <pkg>`); if unfixed upstream, record in `[tool.uv.audit] ignore-until-fixed` with a dated reason (or `ignore` only when proven non-applicable/blocked, per [audit settings](https://docs.astral.sh/uv/reference/settings/#audit)) — never pass CLI `--ignore` or drop `check:vuln`.
- **Upstream & Docs**: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) (`uv`, per [vendor-skills](../../agent-project/references/vendor-skills.md) · [Skills CLI](https://skills.sh/docs/cli)) · [uv docs](https://docs.astral.sh/uv/) · [Releases](https://github.com/astral-sh/uv/releases) ([changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)).
