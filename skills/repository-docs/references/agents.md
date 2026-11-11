# AGENTS.md Guidance

Split instructions cleanly: global persona for personal defaults, project `AGENTS.md` for repo invariants, and skills for reusable procedures. Lead rules with `**<2–6 word rule>**: <detail>` stating the rule (reference lists may lead with path/name).

## Global persona

1. **Ground in real corrections**: derive rules from explicit user requests and repeated corrections, never assistant suggestions or private transcript dumps.
1. **Keep cross-cutting standards**: communication, autonomy, security, taste, and done criteria belong here; tool manuals belong in skills.
1. **Eliminate friction**: replace rigid blanket rules that cause needless questions or unsafe shortcuts with concrete decision criteria, and move procedures to owning skills with routing cues.
1. **Dry-run scenarios**: verify small fixes on dirty trees, read-only reviews, authorized releases, blocked gates, and stop requests each yield an unambiguous action.

## Project instructions

Give agents only what differs from global defaults, keeping one body in `AGENTS.md` (with host symlinks/bridges, never copies):

1. **State scope & stack**: 1-sentence purpose, stack, link to `README.md` setup, and subtree scope for nested `AGENTS.md`.
1. **List verified commands**: install, focused check/test, full gate, build, and watch (`mise` task names), separating local gates from deploy/release commands.
1. **Capture local invariants**: architecture seams, generated files/locks, source vs deployed paths, privacy rules, and top-level layout (linking workflows to `.agents/skills/` or global skills).
1. **Verify & prune**: test safe commands, run link/format checks, and delete copied global rules or nonexistent tasks.
