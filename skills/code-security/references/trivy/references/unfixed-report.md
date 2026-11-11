# Fixed and Unfixed Advisory Report

Keep `check:scan` blocking; emit a separate `HIGH`/`CRITICAL` JSON vuln report (`--exit-code 0` on findings, non-zero on tool/DB/config errors) to an untracked `0600` path outside the repo, retained briefly with no secret scan:

```bash
umask 077
trivy --config trivy.yaml fs --scanners vuln --ignore-unfixed=false --exit-code 0 --format json --output "$REPORT_PATH" .
```
