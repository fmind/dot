---
name: cf
description: "Inspect and manage Cloudflare zones, DNS, Workers, Pages, R2, D1, and Zero Trust with cf."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cf
  created: "2026-11-13"
  updated: "2026-11-13"
---

# Cloudflare (`cf`)

Authenticate per account via named profiles and disable telemetry once per workstation (`cf cli telemetry disable`).

## Commands

```bash
cf -q auth whoami
cf -q auth list
cf -q auth scopes
cf -q zones list
cf -q cli search "workers secrets"
cf -q schema workers secrets update
```

- **Pin account and zone**: pass `--profile <name>` and `-z <zone-id-or-domain>` (or bind a directory with `cf auth activate <profile>`) on customer work so writes cannot hit the wrong account.
- **Keep machine output clean**: `cf` has no `--json` flag; pass `-q` (`--quiet`) to suppress banners and update notices.
- **Discover subcommands and payloads safely**: use `cf cli search <query>` and `cf schema <command ...>`, then test mutations with `--dry-run` or `--local` simulation first.

## Secrets and Guardrails

- **Keep secrets out of `argv`**: avoid `cf workers secrets update <name> --text ...`; write a `0600` temp JSON file (or generate via `dot secret run`) and apply `cf -q workers secrets bulk --worker <script> --secrets @<tmpfile>`, removing the temp file right after.
- **Ask before remote state changes**: require user approval before live DNS, Workers/Pages deploys, cache purges, R2/KV/D1 writes, Zero Trust/WAF/firewall rules, billing reads/writes, `api` writes, or `-y`.

## Documentation

- [Cloudflare CLI (`cf`)](https://developers.cloudflare.com/workers/wrangler/commands/) · [API Docs](https://developers.cloudflare.com/api/)
