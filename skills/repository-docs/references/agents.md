# AGENTS.md Guidance

Keep each instruction layer focused: the global persona owns durable personal preferences, project instructions own repository invariants, and skills own reusable procedures.

## Global persona

1. **Ground preferences**: use explicit requests, repeated corrections, and a bounded sample of user-authored prompts; distinguish these from assistant suggestions, stale plans, or one-off project choices. Do not copy private transcripts into shared files.
1. **Keep frequent decisions close**: communication, initiative, engineering taste, scope, authorization, and completion standards belong in the persona; tool inventories and authoring recipes belong with their owning skills.
1. **Resolve friction**: check whether blanket rules cause unnecessary questions, redundant research, speculative abstractions, or unsafe automation. Preserve the underlying intent with a concrete decision rule.
1. **Offload without losing meaning**: map each removed requirement to an existing skill, move uncovered guidance to its owner, and repair inbound references. Retain only useful routing cues; never require loading the whole catalog.
1. **Review behavior**: walk through a small fix in a dirty tree, an advice-only request, a broad review, an authorized release, a blocked check, and a stop request. Verify each yields a clear next action; prose review and package checks do not establish live host compliance.

## Project instructions

Give an agent the repository-specific information required to change the project correctly without copying global defaults.

1. **Inspect the contract**: read ancestor and local instructions, manifests, mise tasks, hooks, CI, and the relevant source tree; identify rules that differ from global defaults.
1. **State identity and scope**: give a short project purpose, supported stack, and links to human setup documentation; explain which subtree a nested instruction file governs.
1. **Document verified commands**: setup, focused checks, complete gate, build, and watch using actual task names; separate workstation checks and consequential release or deploy operations.
1. **Record local invariants**: architecture seams, generated-file ownership, source versus deployed paths, private-data constraints, and non-obvious validation requirements.
1. **Map the layout**: list important top-level paths with one sentence each; link multi-step workflows to `.agents/skills/<name>/SKILL.md` or the relevant shared skill.
1. **Verify and trim**: run safe documented commands and link or format checks; remove stale advice, copied global rules, and commands the repository does not provide.

Keep one instruction body in `AGENTS.md` and use host bridges instead of copies. Distinguish hard invariants from recommendations, use repository-relative or `~`-relative paths, preserve the repository's Markdown style, and never include credentials or transient session state.
