---
name: xh
description: "Inspect HTTP endpoints with bounded, credential-safe xh requests, and DNS with doggo when a request fails before HTTP."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/xh
  created: "2026-09-05"
  updated: "2026-11-07"
---

# xh HTTP Inspection

Use xh for bounded read-only HTTP inspection. POST, PUT, PATCH, DELETE, uploads, and state-changing bodies need explicit authorization for the exact target and effect.

## Workflow

1. **Start with headers only**: use an explicit trusted URL and a HEAD request with `--print=h`, because piped xh prints only the body and a bare HEAD prints nothing. Always pass `--ignore-stdin`: in a non-TTY shell, such as an agent's, xh otherwise waits on stdin as the request body, ignoring `--timeout`, until the shell closes it (about 300 s).

   ```bash
   xh --ignore-stdin --check-status --timeout 10 --print=h HEAD https://example.com/health
   ```

1. **Limit the displayed body**: request at most 64 KiB and cap displayed output even when a server ignores `Range`; inspect `Location` before adding `--follow`, which can forward credentials to another origin.

   ```bash
   xh --ignore-stdin --check-status --timeout 10 GET https://example.com/api Range:bytes=0-65535 | head -c 65536
   ```

   Read `${PIPESTATUS[0]}` right after the pipeline: `head` owns the pipeline's exit status, so it hides the 4xx/5xx that `--check-status` flags; report truncation separately.

1. **Protect credentials**: pass synthetic or environment-sourced authorization only to the intended origin, and add `--ignore-netrc` to requests that need no credentials, since xh otherwise sends matching `~/.netrc` entries. Use `--print=h` or `--body`; never `--verbose`, `--debug`, `--curl`, sessions, or request-header printing around secrets.

## When the request fails before HTTP

- **Query DNS with doggo**: `doggo example.com. A --timeout=3s --json`, then the same for `AAAA`, separates record families; record NXDOMAIN, SERVFAIL, timeout, answers, and TTL separately. `--ipv4` selects the resolver transport, while `A` selects the record type. Never send private hostnames to public resolvers.
- **Keep TLS verification on**: preserve the original hostname for SNI; `--verify=no`, replacing a trust store, or changing a machine's resolver is a configuration change, not a diagnosis.

## Gotchas

- **Supervise hard deadlines externally**: `--timeout` covers an individual request, including response-body reads in xh 0.26.3, despite its help calling it a connection timeout. Use a process supervisor for a hard deadline across redirects, authentication retries, and output processing.
- **Range does not limit transfer**: a Range request is not a guaranteed transfer limit; the byte cap bounds only displayed output.
- **Avoid persistent sessions**: `--session` persists cookies and credentials; prefer no session, or use `--session-read-only` only with an explicitly approved synthetic fixture.

## Official Skills

xh has no upstream skill bundle. Use the installed CLI and verify flags with `xh --help`.

## Documentation

- [xh](https://github.com/ducaale/xh) · [command reference](https://github.com/ducaale/xh#usage) · [request timeout implementation](https://github.com/ducaale/xh/blob/v0.26.3/src/main.rs) · [Doggo options](https://doggo.mrkaran.dev/docs/guide/reference/)
- Releases: [xh](https://github.com/ducaale/xh/releases) · [changelog](https://github.com/ducaale/xh/blob/master/CHANGELOG.md) · [Doggo](https://github.com/mr-karan/doggo/releases)
- Companion skills: [gws](../gws/SKILL.md) (authenticated Google Workspace operations).
