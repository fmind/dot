---
name: cf
description: "Manage Cloudflare DNS, zones, Workers, Pages, R2, D1, Zero Trust: cf."
---

# Cloudflare (`cf`)

Manage Cloudflare accounts, DNS, Workers, Pages, R2, D1, and Zero Trust via `cf` (not globally installed in `fmind/dot`; pin per project via `mise use --pin npm:cf` or run `npx`). `CF_SEND_TELEMETRY=0` is set globally in `fmind/dot`; run `cf cli telemetry disable` on unconfigured hosts.

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

- **Keep secrets out of argv**: avoid `--text ...`; write a `0600` temp JSON file (or use `with-secret`) and apply `cf -q workers secrets bulk --worker <script> --secrets @<tmpfile>`, then shred/remove the temp file.
- **Piped `cf deploy` skips prompts**: never pipe stdin accidentally into `cf deploy`; require explicit approval before DNS, Workers/Pages deploys, cache purges, R2/KV/D1 writes, Zero Trust/WAF rules, billing reads/writes, `api` writes, or `-y`.

## Documentation

- [Cloudflare CLI (`cf`)](https://github.com/cloudflare/cf) · [Cloudflare API](https://developers.cloudflare.com/api/) · [Workers docs](https://developers.cloudflare.com/workers/) · [cf releases](https://github.com/cloudflare/cf/releases)
- Companions: [auth-status](../../dot-cli/references/auth-status/GUIDE.md), [http-probing](../../full-review/references/http-probing.md), [infra-as-code](../../infra-as-code/SKILL.md).
