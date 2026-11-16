---
name: copier
description: "Author new reusable Copier templates, generate projects, and apply tracked template updates."
---

# Copier

Default for new reusable templates; keep existing `.cruft.json` checkouts on legacy Cookiecutter/Cruft below unless migration is requested (formats and baselines are incompatible). [bootstrap](bootstrap.md) owns generated project setup.

## Workflow

1. **Review before running**: inspect `copier.yml`, rendered paths, tasks, migrations, and Jinja extensions at an immutable commit. Keep `--trust` off unless executable features are reviewed and authorized. Require Copier `>=9.19.0` (earlier versions have untrusted-execution/prefix [advisories](https://github.com/copier-org/copier/security/advisories)).
1. **Author `copier.yml`**: start from [copier.yml](../templates/copier.yml) with `_min_copier_version: "9.19.0"`, `_subdirectory: template` (so Copier never copies template-repo `.github/`, `tests/`, or lockfiles into generated projects), typed validators, `.jinja` suffixes, `_envops: {undefined: jinja2.StrictUndefined}`, and `{{ _copier_conf.answers_file }}.jinja` rendering `{{ _copier_answers | to_nice_yaml }}` for provenance. Never store secrets in answers or examples.
1. **Generate into a fresh disposable directory**:

   ```bash
   copier copy --defaults --vcs-ref <reviewed-commit> --data slug=demo-app --data holder=Example --data description=Demo . ./generated
   ```

1. **Verify output**: check paths, contents, modes, and provenance across default, non-default, and invalid answers, then run the generated project's gate.
1. **Update in an isolated candidate**: run `copier check-update --output-format json`, verify clean Git state, `.copier-answers.yml`, old/target revisions, and `_skip_if_exists`, then run:

   ```bash
   copier update --defaults --vcs-ref <reviewed-commit>
   ```

1. **Verify the update**: inspect the diff, answer-file revision, conflict markers, and `.rej` files, then run the project gate. Qualify reusable templates across two Git revisions with both a surviving local edit and an overlapping conflict edit.

## Gotchas

- **Answers are update state**: commit `.copier-answers.yml`; never hand-edit it. Change one answer without upgrading via `copier update --defaults --vcs-ref=:current: --data name=value` (omitting `--defaults` hangs headless; omitting `:current:` upgrades to the latest tag).
- **Tag selection**: omitting `--vcs-ref` picks the latest PEP 440 Git tag; pass `HEAD` explicitly for unreleased commits.
- **`copier recopy` overwrites local edits**: never use it to dodge merge conflicts.
- **Replay executes both revisions**: updates render old and new templates; review both commits and keep task dependencies reproducible.
- **`--trust` grants code execution**: disabling tasks alone does not make an untrusted template safe (migrations and Jinja extensions still run).

## Documentation

- [Creating templates](https://copier.readthedocs.io/en/stable/creating/) · [Configuration](https://copier.readthedocs.io/en/stable/configuring/) · [Updating projects](https://copier.readthedocs.io/en/stable/updating/) · [Releases](https://github.com/copier-org/copier/releases)

## Legacy Cookiecutter / Cruft Repositories

Maintain existing Cookiecutter / `.cruft.json` checkouts (such as legacy [fmind/cookiecutter-mlops-package](https://github.com/fmind/cookiecutter-mlops-package)); new projects start from [bootstrap](bootstrap.md) + [ml-jobs](../../python-mlops/references/ml-jobs.md), and new reusable templates default to Copier above.

1. **Pin the runner**: run `uvx --from 'cookiecutter==<version>' cookiecutter` or `uvx --from 'cruft==<version>' cruft` with a reviewed exact release (avoid global installs).
1. **Review before rendering**: templates execute hooks, extensions, and template code, so inspect them at an immutable commit and pass `--checkout`. Keep `--accept-hooks no` until hooks are reviewed; disabling hooks alone does not make an untrusted template safe.
1. **Render into a fresh directory**: never use `--overwrite-if-exists`; verify paths, contents, modes, and unresolved markers, then run the generated project's gate.
1. **Update through Cruft in an isolated candidate**: run `cruft check` and `cruft diff` with the reviewed `--checkout`, then `cruft update --checkout <commit> --skip-apply-ask`; inspect conflicts and `.rej` files, never skip failing files to claim success, and never rebuild `.cruft.json` from memory.
1. **Migrate owned templates to Copier**: Cruft has not released since `2.16.0` (2024-12-25) ([Cookiecutter CLI](https://cookiecutter.readthedocs.io/en/stable/cli_options.html) · [Cruft](https://cruft.github.io/cruft/) · [Cookiecutter releases](https://github.com/cookiecutter/cookiecutter/releases) · [Cruft releases](https://github.com/cruft/cruft/releases)).
