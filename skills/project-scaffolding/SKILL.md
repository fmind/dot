---
name: project-scaffolding
description: "Create repos and licenses; manage Copier and Cookiecutter/Cruft templates."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/project-scaffolding
  created: "2026-09-02"
  updated: "2026-11-17"
---

# Project Scaffolding

Create a lean, complete, fully verified repository or maintain its reusable template. Default to Copier for new templates; keep existing Cookiecutter/Cruft projects on their current workflow. Load the matching guide(s) (`bootstrap` + `project-license` for new repos; `copier` for templates) and run `mise run all` on generated projects before reporting done.

## Task guides

<!-- guides:start -->

- [bootstrap](references/bootstrap.md): Create a new repository: location, visibility, stack composition, shared layer, checks, and first push.
- [copier](references/copier.md): Author new reusable Copier templates, generate projects, and apply tracked template updates.
- [project-license](references/project-license/GUIDE.md): Choose, write, and declare a repository LICENSE (MIT, CC-BY-4.0, or proprietary) by namespace and content.

<!-- guides:end -->

## Documentation

- [Copier](https://copier.readthedocs.io/en/stable/) · [SPDX License List](https://spdx.org/licenses/) · [PEP 639 license expressions](https://packaging.python.org/en/latest/specifications/license-expression/) · [Copier releases](https://github.com/copier-org/copier/releases)
- Companions: [python-stack](../python-stack/SKILL.md), [agent-project](../agent-project/SKILL.md), [repository-docs](../repository-docs/SKILL.md), [github-actions](../github-actions/SKILL.md).
