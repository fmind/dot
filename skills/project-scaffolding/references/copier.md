---
name: copier
description: "New reusable templates and tracked updates."
---

# Copier

Copier is the default for new project templates we maintain. Keep existing Cookiecutter templates and `.cruft.json` projects on [Cookiecutter/Cruft](cookiecutter/GUIDE.md) unless migration is explicitly requested; the formats and update baselines are not interchangeable. [project-scaffolding](bootstrap.md) owns the generated project's stack and repository setup.

## Workflow

1. Inspect `copier --help` and the relevant subcommand help. Review the template at an immutable Git revision, including `copier.yml`, rendered paths, tasks, migrations, and Jinja extensions before running it. Keep `--trust` off unless those executable features have been reviewed and their effects are authorized.
1. Author questions and defaults in `copier.yml`, with explicit types and validators where needed. Keep templates deterministic and use `.jinja` for rendered files. Include `{{ _copier_conf.answers_file }}.jinja` rendering `{{ _copier_answers | to_nice_yaml }}` so generated projects record their answers and template provenance. Keep secrets out of stored answers and generated examples.
1. Generate into a fresh disposable directory with explicit answers and a reviewed revision:

   ```bash
   copier copy --defaults --vcs-ref <reviewed-commit> --data project_slug=demo ./template ./generated
   ```

1. Check rendered paths, contents, executable modes, and recorded provenance. Exercise default and non-default answers, invalid input, and the generated project's native gate before delivering the template.
1. For updates, inspect the clean project's Git state, `.copier-answers.yml`, old and target template revisions, and ownership rules such as `_skip_if_exists`. Work in an isolated candidate; from its root run:

   ```bash
   copier update --defaults --vcs-ref <reviewed-commit>
   ```

1. Review the entire diff, answer-file revision, conflict markers, and `.rej` files; resolve conflicts explicitly and run the generated project's gate. Qualify reusable templates with two Git revisions and a local project edit that must survive an update; also exercise an overlapping edit that must surface as a conflict.

## Gotchas

- **Answers are update state**: commit the generated answers file; never hand-edit it to change configuration or invent a migration baseline. Change answers through `copier update --data name=value`.
- **Version selection**: without `--vcs-ref`, Copier selects releases using Git tags and PEP 440 ordering; `HEAD` explicitly opts into unreleased changes.
- **Recopy overwrites**: `copier recopy` bypasses the smart update process and can overwrite project edits. It is not a conflict-resolution shortcut.
- **Replay must work**: updates can render old and new templates and execute their tasks. Keep external dependencies reproducible; review both revisions, not only the target.
- **Trust is execution authority**: tasks, migrations, and extensions can run code. Disabling tasks alone does not make an untrusted template safe.

## Documentation

- [Creating templates](https://copier.readthedocs.io/en/stable/creating/) · [Configuration](https://copier.readthedocs.io/en/stable/configuring/) · [Updating projects](https://copier.readthedocs.io/en/stable/updating/)
- Releases: [Copier](https://github.com/copier-org/copier/releases)
