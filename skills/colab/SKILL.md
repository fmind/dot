---
name: colab
description: "Run code on Colab GPUs or TPUs and track compute units."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/colab
  created: "2026-09-16"
  updated: "2026-11-11"
---

# Google Colab CLI

Inspect sessions or run accelerator workloads with `colab` (this connector owns auth selection, session hygiene, and spend authority; upstream's skill lists full command details).

## Authentication

Always pass global `--auth adc` or `--auth oauth2` before subcommands (CLI 0.8.0 defaults to OAuth). ADC reuses [gcloud](../gcloud/SKILL.md) credentials; run `dot login colab` (`--dry-run` previews) to ensure Colab ADC scopes and verify session access ([Colab ADC](../dot-cli/references/authentication.md#colab-adc)). State lives in `~/.config/colab-cli/`.

## Inspect without allocating

Check `colab version` and `--help`, then query `colab --auth adc sessions`, `status`, and `usage` (check stderr before trusting empty output; never run `colab pay`, which opens a purchase page, or `new`/`run`/`exec` just to inspect).

## Run accelerator work

Confirm authorized accelerator, duration, and budget before allocating:

1. **Prefer ephemeral `colab run`** for scripts that persist their own outputs externally (local VM files vanish on release; shebang `#!/usr/bin/env -S colab --auth adc run --gpu T4 --timeout 3600` works per [python-script](../python-stack/references/python-script/GUIDE.md)):

   ```bash
   colab --auth adc run --gpu T4 --timeout 3600 train.py
   ```

1. **Manage interactive sessions explicitly**: `colab --auth adc new -s <name> --gpu L4` (`--tpu v6e1`), `exec -s <name> -f snippet.py --timeout 600`, `upload`/`download`/`ls`/`status`/`log`, retrieving artifacts before teardown.
1. **Stop and verify release**: run `colab --auth adc stop -s <name>` and recheck `colab --auth adc sessions`—ephemeral `run` suppresses release failures, so exit 0 or "Session terminated" does not prove the VM stopped billing.

## Gotchas

- **Raise the 30s timeout**: `run` and `exec` abort at 30 s unless `--timeout <seconds>` covers the full run.
- **Keep Colab's kernel client**: CLI 0.8.0 pins `jupyter-kernel-client==0.9.0`; do not override it via mise `with`.
- **Guard allocation side doors**: `colab ssh` allocates a VM if the session is missing, and `colab run --keep` skips teardown—both require `colab new` spend authority.
- **Never read `colab.log` into context**: CLI 0.8.0 creates `~/.config/colab-cli/colab.log` (`0600`) with token redaction, but pre-0.8 files (`0644`) and unredacted URLs can still linger; count matches if diagnosing, never print or quote lines.
- **Disposable VMs**: pass minimal task secrets and run `colab drivemount` only when Drive access is required.

## Official Skills

Upstream: `googlecolab/google-colab-cli` (`colab skill`), reviewed and scoped per [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [Colab CLI](https://github.com/googlecolab/google-colab-cli)
- Releases: [google-colab-cli tags](https://github.com/googlecolab/google-colab-cli/tags)
- ML workflows: [python-mlops](../python-mlops/SKILL.md) owns data validation, training, experiments, and model delivery.
- Companion skills: [kaggle](../kaggle/SKILL.md), [hf](../hf/SKILL.md), [python-script](../python-stack/references/python-script/GUIDE.md), [gcloud](../gcloud/SKILL.md).
