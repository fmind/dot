---
name: authentication
description: "Inspect and apply configured provider login, OAuth scopes, and account policy."
---

# Workstation Authentication

Login checks current authentication and scopes before opening a browser. `--force` repeats authentication; `--dry-run` previews possible commands without executing probes. Unknown status fails with recovery guidance instead of starting authentication. Repair or remove environment-token overrides when they prevent OAuth updates.

Workspace project selection uses the setup argument, then `GWS_PROJECT`, then `auth.workspace.project`. GitHub host selection uses `--host`, then `GH_HOST`, then `auth.github.host`. Inspect policy with `dot config show` and edit it with `dot config edit`: `auth.github.scopes`, `auth.github.remove_scopes`, `auth.workspace.scopes`, `auth.workspace.apis`, and `auth.probe_timeout_seconds`. Maps merge with defaults; configured lists replace the entire default list.

The default policy covers repository, publishing, document, mail, calendar, contact, Chat, and Apps Script workflows, including Gmail settings/filter and Chat read-state management. It excludes GitHub repository/package deletion scopes and permits SSH key creation without key administration. Gmail uses `gmail.modify`, which excludes immediate permanent message deletion; full Drive and other editing scopes can still permit destructive operations. OAuth capability does not authorize deletion or contacting others. GCP permissions remain controlled by IAM. Applying configuration does not change issued tokens: authenticate again for new scopes and use `dot setup github` to remove excluded grants. Personal Google accounts need a Workspace policy without `directory.readonly`.
