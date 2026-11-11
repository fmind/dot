---
name: xh
description: "Inspect HTTP endpoints with bounded xh requests and diagnose DNS with doggo."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/xh
  created: "2026-09-05"
  updated: "2026-11-10"
---

# xh HTTP Inspection

Bounded read-only HTTP probing with `xh` (POST, PUT, PATCH, DELETE, uploads, and state-changing calls require explicit target/effect approval).

## Workflow

1. **Probe headers first**: always pass `--ignore-stdin` (non-TTY `xh` otherwise hangs ~300 s waiting on stdin, bypassing `--timeout`) and `--print=h` (piped `xh` omits headers by default):

   ```bash
   xh --ignore-stdin --check-status --timeout 10 --print=h HEAD https://example.com/health
   ```

1. **Bound response bodies to 64 KiB**: cap output even if `Range` is ignored, check `Location` before `--follow` (which can forward credentials cross-origin), and inspect `${PIPESTATUS[0]}` immediately since `head` masks `xh`'s 4xx/5xx exit code:

   ```bash
   xh --ignore-stdin --check-status --timeout 10 GET https://example.com/api Range:bytes=0-65535 | head -c 65536
   ```

1. **Guard credentials**: pass `--ignore-netrc` on unauthenticated calls (`xh` auto-sends matching `~/.netrc` entries), scope auth headers to the exact origin, and never use `--verbose`, `--debug`, `--curl`, sessions, or request-header dumps around secrets.

## When the request fails before HTTP

- **Check DNS via `doggo`**: query `doggo example.com. A --timeout=3s --json` and `AAAA` separately (`--ipv4` sets resolver transport, `A` sets record type), recording NXDOMAIN/SERVFAIL/timeout/TTL without sending private hostnames to public resolvers.
- **Never disable TLS (`--verify=no`)**: keep original SNI hostnames and leave trust stores/system resolvers unchanged during diagnosis.

## Gotchas

- **Wrap multi-hop deadlines externally**: `xh` 0.26.3's `--timeout` bounds one request including body reads, not full redirect/retry chains.
- **Skip `--session`**: persists cookies and auth headers (`--session-read-only` only on approved synthetic fixtures).

## Documentation

- [xh](https://github.com/ducaale/xh) · [command reference](https://github.com/ducaale/xh#usage) · [request timeout implementation](https://github.com/ducaale/xh/blob/v0.26.3/src/main.rs) · [Doggo options](https://doggo.mrkaran.dev/docs/guide/reference/)
- Releases: [xh](https://github.com/ducaale/xh/releases) · [changelog](https://github.com/ducaale/xh/blob/master/CHANGELOG.md) · [Doggo](https://github.com/mr-karan/doggo/releases)
- Companion skills: [gws](../gws/SKILL.md) (authenticated Google Workspace operations).
