---
name: cookiecutter
description: "Generate from existing Cookiecutter templates and update Cruft-tracked projects without losing local edits."
---

# Cookiecutter

Keep existing Cookiecutter templates, such as [fmind/cookiecutter-mlops-package](https://github.com/fmind/cookiecutter-mlops-package), and `.cruft.json` projects on Cookiecutter/Cruft; [Copier](copier.md) is the default for new templates.

1. **Pin the runner**: run `uvx --from 'cookiecutter==<version>' cookiecutter` or `uvx --from 'cruft==<version>' cruft` with a reviewed exact release.
1. **Review before rendering**: templates execute hooks, extensions, and template code, so review them at an immutable commit and pass it with `--checkout`. Use `--accept-hooks no` until the hooks are reviewed; disabling hooks alone does not make a template safe.
1. **Render into a fresh directory**: never use `--overwrite-if-exists`; check paths, content, modes, and unresolved markers, then run the generated project's gate.
1. **Update through Cruft in an isolated candidate**: `cruft check` and `cruft diff` with the reviewed `--checkout`, then `cruft update --checkout <commit> --skip-apply-ask`; review conflicts and `.rej` files, never skip failing files to claim success, and never rebuild `.cruft.json` from memory.
1. **Propose Copier for owned templates**: Cruft has not released since 2.16.0 (2024-12-25).

Docs: [Cookiecutter CLI](https://cookiecutter.readthedocs.io/en/stable/cli_options.html) · [Cruft](https://cruft.github.io/cruft/) · releases: [Cookiecutter](https://github.com/cookiecutter/cookiecutter/releases), [Cruft](https://github.com/cruft/cruft/releases)
