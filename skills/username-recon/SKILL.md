---
name: username-recon
description: "Check usernames across sites with Sherlock (OSINT)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/username-recon
  created: "2026-09-16"
  updated: "2026-10-05"
---

# Public Username Reconnaissance

Use `sherlock-project/sherlock`, distributed as `sherlock-project`, for public username OSINT checks within the requested scope. Keep usernames, sites, time window, and stop conditions explicit, and stop on scope escape or unexpected impact; this reconnaissance authorizes neither exploitation nor other techniques.

## Workflow

1. **Pin the request scope**: establish the exact usernames, selected sites, purpose, and output destination from the request. Treat a username match as a lead, not proof of a person's identity.
1. **Pin and inspect a reviewed release**: inspect `uvx --from 'sherlock-project==<version>' sherlock --help` and `--version`, resolving `<version>` to a reviewed exact release. This pins Sherlock, not its entire dependency graph; use a locked environment when repeatable dependencies are required. Prefer installed help because published website examples may lag the CLI.
1. **Run selected sites with fixed definitions**: review the selected site's destination and detection rule in that release's bundled definitions. Use `--local` to keep those definitions fixed; it does not make the account lookup offline. Run only the selected sites, with a bounded per-request timeout, in a private output directory. For one authorized username, adapt:
   ```bash
   uvx --from 'sherlock-project==<version>' sherlock <username> --local --site GitHub --timeout 10 --output results.txt --txt
   ```
1. **Verify each reported match**: review reported matches against the public profile URL and the site's current response behavior. Record confirmed presence, not-found, and indeterminate errors separately; do not convert timeouts or blocks into absence.
1. **Minimize retained evidence**: retain only the evidence needed for the task and report confidence and lookup date. Test parsing changes with saved HTTP fixtures instead of repeatedly querying real accounts.

## Gotchas

- **A hit is not an identity**: similar handles can belong to unrelated people; do not infer identity, private attributes, or contact details from a hit.
- **Verify export flags before automating**: `--json` selects site definitions; it is not a JSON result-output switch. `--output` only names the file that `--txt` writes, and that file lists claimed URLs only; record not-found and errors from the run output. Verify export flags before automating them.
- **Site definitions drift either way**: without `--local`, Sherlock can fetch current site definitions independently of the pinned package. Bundled definitions can become stale, and local mode bypasses upstream exclusion updates: verify each reported match against the current site response before claiming presence.
- **Keep lookups within request scope**: avoid all-site expansion, automatic browsing, or remote site-definition overrides unless the request requires them; a remote definition controls where requests go. Release checks can still contact upstream in local mode.

## Documentation

- [Usage](https://sherlockproject.xyz/usage) · [Source and installation](https://github.com/sherlock-project/sherlock)
- Releases: [Sherlock](https://github.com/sherlock-project/sherlock/releases)
- Upstream ships no consumer Agent Skill (checked 2026-10-04); community packages are not upstream endorsements.
