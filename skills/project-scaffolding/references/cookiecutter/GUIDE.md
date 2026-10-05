---
name: cookiecutter
description: "Generate from existing Cookiecutter templates and update Cruft-tracked projects without losing local edits."
---

# Cookiecutter

Use Cookiecutter for existing or explicitly requested Cookiecutter templates; [Copier](../copier.md) is the default for new templates we maintain. Generate from reviewed templates with Cookiecutter. For revision tracking, existing `.cruft.json` provenance, and updates that preserve local edits, follow [Cruft updates](references/updates.md). Ordinary application templates use the framework's installed Jinja documentation.

## Workflow

1. **Inspect the template before execution**: source, immutable revision, `cookiecutter.json`, hooks, extensions, and generated destination names. Templates can execute code.
1. **Define required context and defaults**: keep secrets out of context, replay files, and generated examples. Prefer `uvx --from 'cookiecutter==<version>' cookiecutter --help` for an isolated invocation, resolving `<version>` to a reviewed exact release.
1. **Generate into a fresh disposable directory**: for an already reviewed local template, adapt:
   ```bash
   uvx --from 'cookiecutter==<version>' cookiecutter ./template --no-input --accept-hooks no --output-dir ./generated project_slug=demo
   ```
1. **Permit only reviewed hooks**: review their commands and effects first; a template that needs hooks must be tested with those reviewed hooks too. For remote sources, pass the reviewed commit with `--checkout`.
1. **Verify the generated output**: filenames, rendered content, executable modes, and absence of unresolved template markers. Exercise default and non-default context, invalid input, and generation failure without overwriting existing work.
1. **Gate it; adopt Cruft for updates**: run the generated project's native gate. If ongoing template updates are required, generate through Cruft from the start rather than inventing a second tracking file.

## Gotchas

- **Review more than hooks**: disabling hooks alone does not make untrusted templates safe; extensions and template evaluation also need review.
- **Avoid `--overwrite-if-exists`**: it can destroy local edits; use a new output directory for review.
- **Replay is not a full record**: it captures context, not all external dependencies; record the template revision and compatible tool version.

## Official Skills

No consumer Agent Skill was found in the inspected [cookiecutter/cookiecutter](https://github.com/cookiecutter/cookiecutter) repository on 2026-10-04. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [CLI](https://cookiecutter.readthedocs.io/en/stable/cli_options.html) · [Hooks](https://cookiecutter.readthedocs.io/en/stable/advanced/hooks.html)
- Releases: [Cookiecutter](https://github.com/cookiecutter/cookiecutter/releases) · [Cruft](https://github.com/cruft/cruft/releases)
