---
name: ml-jobs
description: "Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture."
---

# Package ML Jobs

Start new ML packages from the [Python foundation](../../python-stack/references/foundation/references/bootstrap.md) and layer [settings.py](../templates/settings.py) at `src/<package>/settings.py`, [pipeline.py](../templates/pipeline.py) at `src/<package>/pipeline.py`, and [test_pipeline.py](../templates/test_pipeline.py) at `tests/test_pipeline.py` (substituting `<package>` in imports):

```bash
UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'polars>=2.1.0' 'pandera[polars]>=0.36.0' 'scikit-learn>=1.9.1' 'pydantic-settings[yaml]>=2.16.3' 'pydantic>=2.14.3'
```

Consult [sources](sources.md) only for architecture patterns from legacy reference repos; extend existing projects in place.

1. **Validate config before side effects**: load and deep-merge YAML layers via `YamlConfigSettingsSource` in [Pydantic Settings](../../python-stack/references/pydantic.md), apply explicit CLI `key=value` overrides last, and validate strictly (`extra="forbid"`, constrained ranges, zero code/expression evaluation). Start tracking, allocate compute, or write outputs only after validation passes.
1. **Separate effectful tasks & prevent leakage**: keep dataset-wide fitted transforms inside scikit-learn `Pipeline`, evaluate metrics exclusively on holdout splits via `JobConfig` fields, keep training/tuning/evaluation/inference/promotion distinct, preserve warnings and non-zero exits, and never log `locals()`.

## Documentation

- [Pydantic Settings YAML](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#yaml-config-source) · [releases](https://github.com/pydantic/pydantic-settings/releases) · Companions: [python-testing](../../python-stack/references/python-testing/GUIDE.md), [argparse](../../python-stack/references/argparse/GUIDE.md), [mise](../../mise/SKILL.md).
