---
name: colab
description: "Operate Colab accelerator sessions, remote execution, artifact transfers, and compute budgets."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/colab
  created: "2026-09-16"
  updated: "2026-09-26"
---

# Google Colab CLI

Use `colab` to inspect existing sessions or run work on an accelerator the workstation lacks. The official Colab skill documents every command; this skill owns authentication, session hygiene, and the spend boundary.

## Inspect without allocating

For session or account inspection, check `colab version` and installed help, then use `colab sessions` and `colab status` with the existing authentication provider. These synchronize session metadata without allocating or stopping a VM. Check authentication diagnostics before interpreting an empty listing as success.

Use `colab --auth adc usage` for compute-unit rate and balance when ADC is the selected provider; substitute `oauth2` for an existing OAuth profile. This command is available in CLI 0.7.4; check installed help on older versions and report a missing capability instead of allocating a VM. `colab pay` opens a purchase page and is not a balance query. Session inspection does not require `new`, `run`, `exec`, or `stop`.

## Run accelerator work

Follow this workflow only when remote execution is in scope; establish the authorized accelerator, duration, and budget before allocation.

1. **Authenticate**: select the existing provider explicitly with the global `--auth oauth2` or `--auth adc` option before every subcommand. CLI 0.7.4 defaults to OAuth; inspect the installed help instead of relying on implicit defaults or upstream main. ADC reuses credentials from [gcloud](../gcloud/SKILL.md); session state lives under `~/.config/colab-cli/`. The examples below assume ADC has been selected.
1. **Prefer ephemeral runs when outputs are persisted by the script**: `colab run` rents a VM, runs the script, and attempts to release it. Save needed artifacts to an authorized durable destination before the script exits; local VM files disappear on release. Use an explicitly managed session when artifacts must be downloaded afterwards. A shebang `#!/usr/bin/env -S colab --auth adc run --gpu T4` supports single-file execution per [python-script](../python-stack/references/python-script/GUIDE.md).

   ```bash
   colab --auth adc run --gpu T4 --timeout 3600 train.py
   ```

1. **Keep a session only while iterating**: `colab --auth adc new -s <name> --gpu L4` (or `--tpu v6e1`), then `colab --auth adc exec -s <name> -f snippet.py --timeout 600`. Use the same explicit provider for `upload`, `download`, `ls`, `status`, and `log`; verify and retrieve needed artifacts before stopping.
1. **Stop what you started and verify release**: `colab --auth adc stop -s <name>`, then refresh `colab --auth adc sessions`; an idle session keeps consuming compute units. CLI 0.7.4's ephemeral cleanup suppresses release errors, so a successful `run` exit or “Session terminated” message is not release proof. Check authentication diagnostics and the backend listing before reporting cleanup complete.

## Gotchas

- **30-second default**: `colab run` and `colab exec` abort code execution after 30 seconds unless `--timeout <seconds>` covers the whole job.
- **Kernel client**: google-colab-cli 0.7.4 pins `jupyter-kernel-client==0.9.0`; let Colab select its compatible client instead of adding a conflicting mise `with` override.
- **Tiers**: accelerator availability depends on the subscription; `colab pay` opens the compute-units page, so treat it as spend.
- **Disposable VM**: keep secrets off the session beyond what the task needs; use `colab drivemount` only when Drive data is required.

## Official Skills

Upstream: `googlecolab/google-colab-cli`, the same source `colab skill` prints. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select only the Colab workflow needed by the project.

## Documentation

- [Colab CLI](https://github.com/googlecolab/google-colab-cli)
- Releases: [google-colab-cli](https://github.com/googlecolab/google-colab-cli/releases)
- ML workflows: [python-mlops](../python-mlops/SKILL.md) owns data validation, training, experiments, and model delivery.
- Companion skills: [kaggle](../kaggle/SKILL.md), [hf](../hf/SKILL.md), [python-script](../python-stack/references/python-script/GUIDE.md), [gcloud](../gcloud/SKILL.md).
