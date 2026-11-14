---
name: cf
description: "Inspect and manage Cloudflare zones, DNS, Workers, Pages, R2, D1, and Zero Trust with cf."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cf
  created: "2026-11-13"
  updated: "2026-11-14"
---

# Cloudflare (`cf`)

Manage Cloudflare accounts, DNS, Workers, Pages, R2, D1, and Zero Trust via `cf` (`CF_SEND_TELEMETRY=0` is set globally in `fmind/dot`; run `cf cli telemetry disable` on unconfigured hosts).

## Commands

```bash
cf -q auth whoami
cf -q auth list
cf -q zones list
cf -q docs search "workers secrets"
cf -q cli search "workers secrets"
cf -q schema workers secrets update
```

- **Pin account and zone**: pass `--profile <name>` and `-z <zone-id-or-domain>` (or `cf auth activate <profile>`) on customer work so writes cannot hit the wrong account; prefer `cf auth login --use-keyring` for token storage.
- **Quiet and JSON output**: pass `-q` (`CF_QUIET=1`) to suppress update banners; `cf` emits machine-readable JSON on stdout by default on supported commands.
- **Discover safely**: query offline CLI help (`cf -q cli search`), payload schemas (`cf -q schema`), and docs (`cf -q docs search`), and test mutations with `--dry-run` or `--local`.

## Secrets and Guardrails

- **Keep secrets out of argv**: avoid `--text ...`; write a `0600` temp JSON file (or use `dot secret run`) and apply `cf -q workers secrets bulk --worker <script> --secrets @<tmpfile>`, then shred/remove the temp file.
- **Piped `cf deploy` skips prompts**: never pipe stdin accidentally into `cf deploy`; require explicit approval before DNS, Workers/Pages deploys, cache purges, R2/KV/D1 writes, Zero Trust/WAF rules, billing reads/writes, `api` writes, or `-y`.

## Documentation

- [Cloudflare CLI (`cf`)](https://github.com/cloudflare/cf) · [Cloudflare API](https://developers.cloudflare.com/api/)
