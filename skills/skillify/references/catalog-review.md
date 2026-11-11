# Catalog Growth and Usage Review

Audit discovery cost and local activation evidence on demand (never as a background collector).

## Review

1. **Measure context**: run `dot agent context --source . --project . --details` (add `--check` for [context budgets](../../dot-cli/references/context.md); omit `--source` for deployed roots) and compare startup metadata vs on-demand body/guide costs against the prior revision.
1. **Count observed loads**: over an explicit window and available local hosts, run `python3 -I ~/.agents/skills/skillify/scripts/skill_loads.py --days 30` ([skill_loads.py](../scripts/skill_loads.py); `--json`, `--skills <dir>`). It counts agy, Claude Code, and Pi sessions whose tool calls read `SKILL.md` or invoked `Skill`, excluding audit sessions loading ≥8 skills (`--audit`) and printing only skill names and counts (never transcripts or paths).
1. **Weigh value vs frequency**: zero loads on one machine do not prove uselessness (rare security/recovery skills earn their slot; frequent generic reads can still waste tokens).
1. **Trim before adding**: tighten descriptions, move niche detail to `references/`, or use `.agents/skills/` before admitting a global owner under [package rules](package-rules.md#categories-and-scope).
1. **Verify routing**: run [adoption checks](adoption-check.md) (12–20 probes across explicit, implicit, neighbor, and no-skill prompts for broad reorganizations). Record window, coverage, before/after token cost, owner/trigger, and validation in the PR or task report.
