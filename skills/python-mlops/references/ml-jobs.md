---
name: ml-jobs
description: "Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture."
---

# Package ML Jobs

Use the [source map](sources.md) to choose between the Cookiecutter foundation and the bike-demand reference implementation. Extend an existing project in place; template generation and updates belong to [project-scaffolding](../../project-scaffolding/SKILL.md), and general package layout belongs to [python-stack](../../python-stack/references/foundation/GUIDE.md).

1. **Extract the demonstrated workflow**: keep exploration in the notebook; move reusable transformations, schemas, fitting, and predictions into importable modules. Preserve results on a small fixture before adding new architecture. Depend on project-selected ML libraries, not the entire course stack.
1. **Separate effects from computation**: keep model/data logic independent of storage and tracking. Use thin readers/writers and job orchestration only where boundaries recur. The reference `core/`, `io/`, `jobs/`, and `utils/` layout is an example; do not create abstract bases or empty layers for a single function.
1. **Validate configuration before effects**: in the reference pattern, merge YAML files in supplied order, apply explicit overrides last, resolve OmegaConf interpolation, then validate with Pydantic. Document the actual project's defaults and precedence. Reject unknown fields and job kinds where appropriate; constrain paths and selected implementations. Do not resolve arbitrary imports or executable expressions from untrusted configuration. Start tracking, allocate compute, or write outputs only after validation succeeds.
1. **Keep jobs composable**: a CLI parses and validates, a job orchestrates, and functions implement the work. Inject readers, writers, and tracker clients where tests need isolation. Close every acquired resource on success, partial startup failure, and cancellation. Return a small typed result with metrics and artifact references; never return or log `locals()` containing datasets, credentials, and clients.
1. **Expose actual effects**: separate training, tuning, evaluation, inference, and promotion tasks. Inspect task dependencies and configuration before invoking an aggregate command. The reviewed reference's `mise run project` promotes before evaluating; adapt the sequence to evaluate the exact candidate before any alias mutation. Preserve warnings and failure exit codes.
1. **Qualify the packaged job**: use tiny local data and a disposable tracker. Test invalid configuration before I/O, malformed data, an output-write failure, cleanup, and a successful train/save/reload/predict path. Run the project's relevant static checks and build; execute the built artifact outside the source import path when packaging changes. A successful template render alone does not qualify its ML runtime.

## Documentation

- [Pydantic guide](../../python-stack/references/pydantic.md) · [OmegaConf usage and merging](https://omegaconf.readthedocs.io/en/latest/usage.html) · [OmegaConf releases](https://github.com/omry/omegaconf/releases).
- [python-testing](../../python-testing/SKILL.md), [cli-development](../../cli-development/SKILL.md), and [mise](../../mise/SKILL.md) own the shared implementation procedures.
