---
name: ml-jobs
description: "Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture."
---

# Package ML Jobs

Start new ML packages from the [Python foundation](../../python-stack/references/foundation/references/bootstrap.md) and layer [settings.py](../templates/settings.py), [pipeline.py](../templates/pipeline.py), and [test_pipeline.py](../templates/test_pipeline.py):

```bash
UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'polars>=2.1.0' 'pandera[polars]>=0.36.0' 'scikit-learn>=1.9.1' 'omegaconf>=2.3.0' 'pydantic>=2.14.3'
```

Consult [sources](sources.md) only for architecture patterns from legacy reference repos; extend existing projects in place.

1. **Validate config before side effects**: merge YAML files in order, apply explicit overrides last, resolve OmegaConf interpolation, then validate with [Pydantic](../../python-stack/references/pydantic.md) (reject unknown fields with `extra="forbid"`, constrain paths/job kinds, and never resolve arbitrary imports or executable expressions from untrusted config). Start tracking, allocate compute, or write outputs only after validation passes.
1. **Separate effectful tasks**: keep training, tuning, evaluation, inference, and promotion distinct (unlike the legacy `mise run project`, evaluate the exact candidate before mutating any alias). Keep warnings visible (never blanket-ignore `UserWarning`), preserve non-zero exit codes, and never return or log `locals()`.

## Documentation

- [OmegaConf merging](https://omegaconf.readthedocs.io/en/latest/usage.html) · [releases](https://github.com/hydra-ecosystem/omegaconf/releases) · Companions: [python-testing](../../python-stack/references/python-testing/GUIDE.md), [argparse](../../python-stack/references/argparse/GUIDE.md), [mise](../../mise/SKILL.md).
