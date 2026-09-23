---
name: ast-grep
description: "Find and safely rewrite Python syntax with ast-grep patterns and rules."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/ast-grep
  created: "2026-09-03"
  updated: "2026-09-23"
---

# ast-grep

Structural code search and rewrite: a pattern is real code with meta-variables, matched against the syntax tree. A call-expression pattern distinguishes a call from similar text inside a string or comment; string and comment nodes can also be matched deliberately. Use it where `rg` gives false positives; plain text search stays with `rg`.

## Commands

```bash
ast-grep run -p 'print($$$ARGS)' -l python                                      # search; run is the default subcommand
ast-grep run -p 'print($$$ARGS)' -r 'logger.info($$$ARGS)' -l python             # dry run: prints the diff, changes nothing
ast-grep run -p 'print($$$ARGS)' -r 'logger.info($$$ARGS)' -l python --update-all # apply after reviewing the dry run (-i to confirm per hunk)
ast-grep run -p 'os.getenv($KEY)' -l python --json=compact                       # structured output; --json=stream gives one object per line
ast-grep scan                                                                    # every rule in sgconfig.yml
ast-grep scan -r rules/no-print.yml --format github                              # one rule file; GitHub annotations in CI
```

## Workflow

1. **Write the pattern as code**: `$NAME` matches one node, `$$$NAME` a sequence (arguments, statements), `$_` a node without binding; always pass `-l <lang>` so the pattern parses in the right grammar, and use `--debug-query=ast` when a pattern that should match does not.
1. **Search first**: run without `-r`, read the matches with `-C 2` for context, and tune `--globs` or `--no-ignore` when files are skipped.
1. **Rewrite in two steps**: add `-r` to see the diff, then `--update-all` (or `-i` for an interactive session); captured meta-variables are reused in the replacement.
1. **Promote to a rule**: for a lint or a repeated refactor, `ast-grep new project` scaffolds `sgconfig.yml` and `rules/`; a rule file has `id`, `language`, `rule` (`pattern`, `kind`, `inside`, `has`, `not`), optional `fix`, `severity`, and `message`; `ast-grep test` runs its `valid` and `invalid` cases.
1. **Wire into the gate**: run `ast-grep scan` inside `check:lint` (see [mise](../mise/SKILL.md)) so hooks and CI apply the same rules.

## Gotchas

- **Meta-variables are uppercase**: `$a` is plain text; `$A`, `$ARGS`, `$_` are meta-variables.
- **Pattern must be a complete node**: `foo(` does not parse; match `foo($$$)` and narrow with `--selector`.
- **Rewrite scope**: `-r` replaces the whole matched node, not a substring inside it.
- **Syntax is not name resolution**: inspect imports, aliases, and shadowed names before rewriting; identical syntax can refer to different functions.
- **Language id**: pass `-l python` for inline patterns; under `scan`, the `.py` extension selects the grammar.

## Official Skills

Upstream: `ast-grep/agent-skill`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the structural-search guidance.

## Documentation

- [ast-grep guide](https://ast-grep.github.io/guide/introduction.html) · [Pattern syntax](https://ast-grep.github.io/guide/pattern-syntax.html) · [Rule reference](https://ast-grep.github.io/reference/rule.html) · [Languages](https://ast-grep.github.io/reference/languages.html)
- Releases: [ast-grep](https://github.com/ast-grep/ast-grep/releases) · [changelog](https://github.com/ast-grep/ast-grep/blob/main/CHANGELOG.md)
- Companion skills: [repository-maintenance](../repository-maintenance/SKILL.md) (repository simplification), [python-stack](../python-stack/references/foundation/GUIDE.md) (Python quality gate).
