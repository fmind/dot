---
name: colab
description: "Operate Colab accelerator sessions, remote execution, artifact transfers, and compute budgets."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/colab
  created: "2026-09-16"
  updated: "2026-09-23"
---

# Google Colab CLI

Use `colab` to inspect existing sessions or run work on an accelerator the workstation lacks. The official Colab skill documents every command; this skill owns authentication, session hygiene, and the spend boundary.

## Inspect without allocating

For session or account inspection, check `colab version` and installed help, then use `colab sessions` and `colab status` with the existing authentication provider. These synchronize session metadata without allocating or stopping a VM. Check authentication diagnostics before interpreting an empty listing as success.

The installed CLI 0.6.0 has no compute-balance command; current upstream documents `colab usage` for usage rate and balance. Check that `usage` exists in the installed help before using it. Otherwise use an already available, authorized provider interface or report the missing capability; `colab pay` opens a purchase page and is not a balance query. Session inspection does not require `new`, `run`, `exec`, or `stop`.

## Run accelerator work

Follow this workflow only when remote execution is in scope; establish the authorized accelerator, duration, and budget before allocation.

1. **Authenticate**: select the existing provider explicitly with the global `--auth oauth2` or `--auth adc` option before the subcommand. Version 0.6.0 defaults to OAuth; current upstream documents ADC as the default, so do not rely on the implicit choice across upgrades. ADC reuses credentials from [gcloud](../gcloud/SKILL.md); session state lives under `~/.config/colab-cli/`.
1. **Prefer ephemeral runs**: `colab run` rents a VM, runs the script, and releases it; a shebang `#!/usr/bin/env -S colab run --gpu T4` makes a single file self-contained per [python-script](../python-stack/references/python-script/GUIDE.md).

   ```bash
   colab run --gpu T4 --timeout 3600 train.py
   ```

1. **Keep a session only while iterating**: `colab new -s <name> --gpu L4` (or `--tpu v6e1`), then `colab exec -s <name> -f snippet.py --timeout 600`, `colab upload`, `colab download`, and `colab ls`.
1. **Stop what you started**: `colab sessions` then `colab stop -s <name>`; an idle session keeps consuming compute units. Run `colab status` before claiming a job finished.
1. **Verify**: `colab log` shows the history; download the artifacts before stopping the session.

## Gotchas

- **30-second default**: `colab run` and `colab exec` abort code execution after 30 seconds unless `--timeout <seconds>` covers the whole job.
- **Pinned dependency**: mise uses `with = ["jupyter-kernel-client==0.15.0"]` to retain the compatible client on every reinstall, because the format-1 mise lockfile pins only the tool version, not its dependencies; 1.0.0 renamed the client class and breaks every session.
- **Tiers**: accelerator availability depends on the subscription; `colab pay` opens the compute-units page, so treat it as spend.
- **Disposable VM**: keep secrets off the session beyond what the task needs; use `colab drivemount` only when Drive data is required.

## Official Skills

Upstream: `googlecolab/google-colab-cli`, the same source `colab skill` prints. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select only the Colab workflow needed by the project.

## Documentation

- [Colab CLI](https://github.com/googlecolab/google-colab-cli)
- Releases: [google-colab-cli](https://github.com/googlecolab/google-colab-cli/releases)
- ML workflows: [python-mlops](../python-mlops/SKILL.md) owns data validation, training, experiments, and model delivery.
- Companion skills: [kaggle](../kaggle/SKILL.md), [hf](../hf/SKILL.md), [python-script](../python-stack/references/python-script/GUIDE.md), [gcloud](../gcloud/SKILL.md).
