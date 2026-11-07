---
name: ml-jobs
description: "Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture."
---

# Package ML Jobs

Use the [source map](sources.md) to choose between the Cookiecutter foundation and the bike-demand reference implementation. Extend an existing project in place; template generation and updates belong to [project-scaffolding](../../project-scaffolding/SKILL.md), and general package layout belongs to [python-stack](../../python-stack/references/foundation/GUIDE.md).

1. **Validate configuration before effects**: in the reference pattern, merge YAML files in supplied order, apply explicit overrides last, resolve OmegaConf interpolation, then validate with Pydantic. Document the actual project's defaults and precedence. Reject unknown fields and job kinds where appropriate; constrain paths and selected implementations. Do not resolve arbitrary imports or executable expressions from untrusted configuration. Start tracking, allocate compute, or write outputs only after validation succeeds.
1. **Expose actual effects**: separate training, tuning, evaluation, inference, and promotion tasks. Inspect task dependencies and configuration before invoking an aggregate command. The reviewed reference's `mise run project` promotes before evaluating; adapt the sequence to evaluate the exact candidate before any alias mutation. Preserve warnings (do not adopt the reference's blanket `UserWarning` filter) and failure exit codes. Never return or log `locals()` containing datasets, credentials, and clients.

## Documentation

- [Pydantic guide](../../python-stack/references/pydantic.md) · [OmegaConf usage and merging](https://omegaconf.readthedocs.io/en/latest/usage.html) · [OmegaConf releases](https://github.com/hydra-ecosystem/omegaconf/releases).
- [python-testing](../../python-stack/references/python-testing/GUIDE.md), [typer](../../python-stack/references/typer/GUIDE.md), and [mise](../../mise/SKILL.md) own the shared implementation procedures.
