---
name: ml-jobs
description: "Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture."
---

# Package ML Jobs

Consult [sources](sources.md) for the Cookiecutter foundation vs bike-demand reference. Extend existing projects in place; [project-scaffolding](../../project-scaffolding/SKILL.md) owns templates and [python-stack](../../python-stack/references/foundation/GUIDE.md) owns package layout.

1. **Validate config before side effects**: merge YAML files in order, apply explicit overrides last, resolve OmegaConf interpolation, then validate with [Pydantic](../../python-stack/references/pydantic.md) (reject unknown fields, constrain paths/job kinds, and never resolve arbitrary imports or executable expressions from untrusted config). Start tracking, allocate compute, or write outputs only after validation passes.
1. **Separate effectful tasks**: keep training, tuning, evaluation, inference, and promotion distinct (unlike the reference's `mise run project`, evaluate the exact candidate before mutating any alias). Keep warnings visible (never blanket-ignore `UserWarning`), preserve non-zero exit codes, and never return or log `locals()`.

## Documentation

- [OmegaConf merging](https://omegaconf.readthedocs.io/en/latest/usage.html) · [releases](https://github.com/hydra-ecosystem/omegaconf/releases) · Companions: [python-testing](../../python-stack/references/python-testing/GUIDE.md), [argparse](../../python-stack/references/argparse/GUIDE.md), [mise](../../mise/SKILL.md).
