---
name: xh
description: Inspect HTTP endpoints with bounded, credential-safe xh requests. Use for read-only API headers, status, and small response checks.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/xh
  created: "2026-09-05"
  updated: "2026-09-05"
---

# xh HTTP Inspection

Use xh for bounded read-only HTTP inspection; debugging a known failure belongs to [systematic-debugging](../systematic-debugging/SKILL.md), and API research to [technical-research](../technical-research/SKILL.md).

## Workflow

1. **Confirm the target**: use an explicit trusted URL, ignore stdin, and start with headers so redirects and advertised size are visible without fetching a body.

   ```bash
   xh --ignore-stdin --check-status --timeout 10 HEAD https://example.com/health
   ```

1. **Limit the displayed body**: request at most 64 KiB and cap displayed output even when a server ignores `Range`; do not add `--follow` until the redirect target is reviewed.

   ```bash
   xh --ignore-stdin --check-status --timeout 10 GET https://example.com/api Range:bytes=0-65535 | head -c 65536
   ```

1. **Protect credentials**: pass synthetic or environment-sourced authorization only to the intended origin. Use `--print=h` or `--body`; never `--verbose`, `--debug`, `--curl`, sessions, or request-header printing around secrets.
1. **Interpret honestly**: `--timeout` bounds connection establishment, while the byte cap bounds displayed output. Use a process supervisor for a hard wall-clock deadline; a Range request is not a guaranteed transfer limit. In Bash, retain `PIPESTATUS` immediately after the pipeline and report truncation/SIGPIPE separately from HTTP success. Record status, relevant response headers, truncation, and any untested redirect or authentication boundary.
1. **Require authority for writes**: POST, PUT, PATCH, DELETE, uploads, and state-changing form or JSON bodies need explicit authorization for the exact target and effect.

## Gotchas

- `--follow` can forward a request to another origin; inspect `Location` first and never follow an untrusted redirect with credentials.
- `--verify=no` disables TLS verification and is not an acceptable workaround.
- `--session` persists cookies and credentials; prefer no session, or use `--session-read-only` only with an explicitly approved synthetic fixture.
- A truncated body is inspection evidence, not proof that the full response is valid.

## Official Skills

xh has no upstream skill bundle. Use the installed CLI and verify flags with `xh --help`.

## Documentation

- [xh](https://github.com/ducaale/xh) · [command reference](https://github.com/ducaale/xh#usage)
- Companion skills: [technical-research](../technical-research/SKILL.md), [systematic-debugging](../systematic-debugging/SKILL.md), [gws](../gws/SKILL.md) (authenticated Google Workspace operations).
