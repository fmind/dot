# Fixed and Unfixed Advisory Report

Keep the normal `check:scan` policy blocking and unchanged. Generate a separate JSON vulnerability-only report with the same configuration, severity, scope, and exclusions while overriding only advisory visibility and finding exit status:

```bash
umask 077
trivy --config trivy.yaml fs --scanners vuln --ignore-unfixed=false --exit-code 0 --format json --output "$REPORT_PATH" .
```

An advisory finding does not fail this informational command, but a Trivy execution, database, configuration, or output failure still does. Write the report outside the scanned tree, retain it briefly, and never upload secret-scan output. This remains a `HIGH`/`CRITICAL` report under the shared policy, not an all-severity audit.
