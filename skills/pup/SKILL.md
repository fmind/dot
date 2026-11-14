---
name: pup
description: "Query Datadog logs, metrics, traces, monitors, incidents, and LLM observability with pup."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/pup
  created: "2026-11-13"
  updated: "2026-11-14"
---

# Datadog (`pup`)

Use `pup` with OAuth2 PKCE (`pup auth login --read-only --site <site> [--org <name>]`), never long-lived `DD_API_KEY`/`DD_APP_KEY` env vars unless CI requires service-account keys. Tokens live in `~/.config/pup/` (`0600`).

## Commands

```bash
pup auth status --site datadoghq.eu
pup --read-only --no-envelope logs search --query "status:error service:api" --from 1h --to now --limit 50
pup --read-only --jq '.data' metrics query --query "avg:system.cpu.user{*}" --from 1h --to now
pup --read-only monitors list --limit 25
```

- Pass `--read-only` on investigative/triage runs to block writes client-side; wrap `--no-envelope` (`PUP_NO_ENVELOPE=1`) and `--jq '<expr>'` to unwrap `{status, data, metadata}`.
- Redirected pipes keep JSON (`-o json`); `--verbose` logs rate-limit headers to stderr. Pin `DD_SITE`/`--site` and `--org <name>` explicitly.

## Guardrails

- **Always bound windows and counts**: specify `--from`/`--to` and `--limit` on `logs`, `traces`, `ddsql`, `rum`, and `llm-obs` queries before summarizing.
- **Never auto-trust unknown gateways**: only pass `--trust-site` after the user explicitly verifies a non-Datadog gateway host.
- **Never dump credentials**: never inspect `~/.config/pup/` or print secrets from `pup api-keys` / `pup app-keys`.
- **Ask before writes or external AI routing**: require approval before `-y`, creating/mutating `monitors`, `downtime`, `incidents`, `dashboards`, `workflows`, `data-deletion`, or sending internal context to `pup bits` / `pup acp`.

## Documentation

- [Datadog CLI (`pup`)](https://github.com/DataDog/pup)
