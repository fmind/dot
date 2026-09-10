---
name: cookiecutter
description: Generate projects with Cookiecutter. Use for Jinja templates, context variables, hooks, replayable scaffolding, and template fixture tests.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cookiecutter
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Cookiecutter

Use Cookiecutter for project generation; [cruft](../cruft/SKILL.md) owns tracking template revisions and applying later updates, and [jinja](../jinja/SKILL.md) owns reusable template language and rendering guidance.

## Workflow

1. Inspect the template source, immutable revision, `cookiecutter.json`, hooks, extensions, and generated destination names before execution. Templates can execute code.
1. Define required context and defaults; keep secrets out of context, replay files, and generated examples. Prefer `uvx cookiecutter --help` for an isolated invocation.
1. Generate into a fresh disposable directory. For an already reviewed local template, adapt:
   ```bash
   uvx cookiecutter ./template --no-input --accept-hooks no --output-dir ./generated project_slug=demo
   ```
1. Permit hooks only after reviewing their commands and effects; a template that needs hooks must be tested with those reviewed hooks too. For remote sources, pass the reviewed commit with `--checkout`.
1. Verify filenames, rendered content, executable modes, and absence of unresolved template markers. Exercise default and non-default context, invalid input, and generation failure without overwriting existing work.
1. Run the generated project's native gate. If ongoing template updates are required, generate through Cruft from the start rather than inventing a second tracking file.

## Gotchas

- Disabling hooks alone does not make untrusted templates safe; extensions and template evaluation also need review.
- `--overwrite-if-exists` can destroy local edits; use a new output directory for review.
- Replay captures context, not all external dependencies; record the template revision and compatible tool version.

## Official Skills

No consumer Agent Skill was found in the inspected [cookiecutter/cookiecutter](https://github.com/cookiecutter/cookiecutter) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [CLI](https://cookiecutter.readthedocs.io/en/stable/cli_options.html) · [Hooks](https://cookiecutter.readthedocs.io/en/stable/advanced/hooks.html)
