---
name: http-probing
description: "Probe HTTP with xh, run hurl smoke checks, query DNS with doggo."
---

# HTTP & DNS Probing

Bounded read-only HTTP probing with `xh` and repeatable smoke checks with `hurl` (POST, PUT, PATCH, DELETE, uploads, and state-changing calls require explicit target/effect approval).

## Workflow

1. **Probe headers first**: always pass `--ignore-stdin` (non-TTY `xh` otherwise hangs ~300 s waiting on stdin, bypassing `--timeout`) and `--print=h` (piped `xh` omits headers by default):

   ```bash
   xh --ignore-stdin --ignore-netrc --check-status --timeout 10 --print=h HEAD https://example.com/health
   ```

1. **Bound response bodies to 64 KiB**:
   - Pass `--print=hb` so status and headers stay visible when piped, and cap output even if `Range` is ignored (write to a temp file when JSON parsing needs an un-truncated body).
   - Check `Location` before `--follow` (which can forward credentials cross-origin).
   - Inspect `${PIPESTATUS[0]}` (bash) or `$pipestatus[1]` (zsh/fish) immediately because `head` masks `xh`'s 4xx/5xx exit code (exit `141` `SIGPIPE` is expected when `head -c` truncates a `> 64 KiB` `200 OK` body):

   ```bash
   xh --ignore-stdin --ignore-netrc --check-status --timeout 10 --print=hb GET https://example.com/api Range:bytes=0-65535 | head -c 65536
   ```

1. **Assert repeatable smoke checks with hurl**: run plain-text Hurl suites for deployment health, header, and JSONPath gates instead of brittle shell pipelines (`hurl` is project-specific—pin via `mise use --pin hurl` in repos with committed `.hurl` suites; use `xh` for ad-hoc probes outside a `hurl`-pinned repo since global `mise` runs locked), and gate persisted files with `hurlfmt --check <suite.hurl>` (`hurlfmt --in-place` when editing):

   ```bash
   printf 'GET https://example.com/health\nHTTP 200\n[Asserts]\njsonpath "$.status" == "ok"\n' | hurl --test --max-time 10
   ```

1. **Guard credentials**: pass `--ignore-netrc` on unauthenticated calls (`xh` auto-sends matching `~/.netrc` entries), pass Hurl secrets via `--variable` from `with-secret` environment variables rather than committed files, scope auth headers to the exact origin, and never use `--verbose`, `--debug`, `--curl`, sessions, or request-header dumps around secrets.

## When the request fails before HTTP

- **Check DNS via `doggo`**: query `doggo example.com. A --timeout=3s --json` and `AAAA` separately (`--ipv4` sets resolver transport, `A` sets record type), recording NXDOMAIN/SERVFAIL/timeout/TTL without sending private hostnames to public resolvers.
- **Never disable TLS (`--verify=no` or `--insecure`)**: keep original SNI hostnames and leave trust stores/system resolvers unchanged during diagnosis.

## Gotchas

- **Wrap multi-hop deadlines externally**: `xh` 0.26.3's `--timeout` bounds one request including body reads, not full redirect/retry chains; pass `--max-time` (and `--location-trusted` never) on `hurl`.
- **Skip `--session`**: persists cookies and auth headers (`--session-read-only` only on approved synthetic fixtures).

## Documentation

- [xh](https://github.com/ducaale/xh) · [command reference](https://github.com/ducaale/xh#usage) · [request timeout implementation](https://github.com/ducaale/xh/blob/v0.26.3/src/main.rs) · [Hurl manual](https://hurl.dev/docs/manual.html) · [Doggo options](https://doggo.mrkaran.dev/docs/guide/reference/)
- Releases: [xh](https://github.com/ducaale/xh/releases) · [changelog](https://github.com/ducaale/xh/blob/master/CHANGELOG.md) · [Hurl](https://github.com/Orange-OpenSource/hurl/releases) · [Doggo](https://github.com/mr-karan/doggo/releases)
- Companion skills: [gws](../../gws/SKILL.md) (authenticated Google Workspace operations).
