---
name: username-recon
description: "Check public usernames with Sherlock; scope searches, verify matches, and preserve evidence."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/username-recon
  created: "2026-09-16"
  updated: "2026-09-19"
---

# Public Username Reconnaissance

Use `sherlock-project/sherlock`, distributed as `sherlock-project`, for public username checks within the requested scope.

Keep targets, techniques, time window, and stop conditions explicit. Reconnaissance does not authorize exploitation. Stop on scope escape or unexpected impact; another technique needs its own bounded procedure.

## Workflow

1. Establish the exact usernames, selected sites, purpose, and output destination from the request. Treat a username match as a lead, not proof of a person's identity.
1. Inspect `uvx --from 'sherlock-project==<version>' sherlock --help` and `--version`, resolving `<version>` to a reviewed exact release so a run never executes newly published code; use the installed help because published website examples may lag the CLI.
1. Run only the selected sites, with a bounded per-request timeout, in a private output directory. For one authorized username, adapt:
   ```bash
   uvx --from 'sherlock-project==<version>' sherlock <username> --site GitHub --timeout 10 --output results.txt
   ```
1. Review reported matches against the public profile URL and the site's current response behavior. Record confirmed presence, not-found, and indeterminate errors separately; do not convert timeouts or blocks into absence.
1. Retain only the evidence needed for the task and report confidence and lookup date. Test parsing changes with saved HTTP fixtures instead of repeatedly querying real accounts.

## Gotchas

- Similar handles can belong to unrelated people; do not infer identity, private attributes, or contact details from a hit.
- `--json` selects site definitions; it is not a JSON result-output switch. Verify export flags before automating them.
- Avoid all-site expansion, automatic browsing, or remote site-definition overrides unless the request requires them; a remote definition controls where requests go.

## Official Skills

No consumer Agent Skill was found in the inspected [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Usage](https://sherlockproject.xyz/usage) · [Source and installation](https://github.com/sherlock-project/sherlock)
- Releases: [Sherlock](https://github.com/sherlock-project/sherlock/releases)
