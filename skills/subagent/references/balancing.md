# Severity and Priority Balancing

`P0`–`P2` measures **defect severity within one reviewer lens**; the coordinator sets **action priority across lenses** using optional project `Priorities` from `AGENTS.md` (or the user prompt). Reviewers ignore `Priorities` and stay strictly single-lens—only the coordinator balances trade-offs.

## Canonical Severity Scale

| Severity | Lens meaning                                   | Universal bar                                                                                                                | Coordinator action                                                                                    |
| -------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **`P0`** | Severe, irreversible, or trust-destroying harm | Active exploit, secret/PII/client leak, data loss/corruption, broken primary flow/build, fabricated proof/math, legal breach | Verify truth **and** severity; real `P0`s always block (unless user/`SECURITY.md` explicitly accepts) |
| **`P1`** | Material defect or broken contract             | Reachable bug, broken API/CLI/UX/a11y contract, reliability/perf flaw, dropped scope, major clarity/structure gap            | Fix by default; arbitrate cross-lens collisions or costly fixes via optional `Priorities`             |
| **`P2`** | Non-blocking improvement or cleanup            | Dead code/prose, secondary edge case, minor perf/ergonomics/maintainability gap                                              | Apply cheap, safe fixes in one pass without re-review; defer rest silently or to `## Suggestions`     |

Reviewers omit nits (no `P3` tier); coordinators ignore them.

## Optional Project Priorities & Axis Map

Read ranked `Priorities` from project `AGENTS.md` (e.g., `UX >= Security > Stability > Simplicity > Cost`) or the user prompt when present. When omitted, infer from project type, fix clear `P1`s normally, and escalate genuine cross-lens `P1` collisions under `## Decisions`.

- **UX**: `frontend`, `cli`, `api`, `human`, `docs`, `visuals`, `spec`, `proposal`.
- **Security**: `security`, `compliance`, `cicd`, `agents` (prompt/MCP ACLs), `shell` (injection).
- **Stability**: `code`, `python`, `shell`, `test`, `sre`, `architecture`, `data`, `containers`, `terraform`, `agents`, `completeness`, `factcheck`.
- **Simplicity**: `simplicity`, `skill`, `supagent`.
- **Performance**: `sre`, `frontend` (CWV), `mlops`.
- **Cost**: `finops`, `mlops`, `analytics`.
- **Speed**: iteration/scope velocity (governs deferrals under rule 3 rather than a dedicated reviewer lens).

## Coordinator Arbitration Rules

1. **Verify `P0` severity**: if a lens-local `P0` is over-calibrated for the repo's risk tier (e.g., cold-path timeout on a spike) and carries no severe harm in the table above, downgrade it to `P1` with rationale in `Trade-Offs`; never downgrade genuine security, leak, data-loss, or fabrication `P0`s.
1. **Resolve conflicting `P1`s**: when `A > B`, higher priority wins (keep a cheap mitigation for `B` if possible, else defer `B` with its cited `rule:`); when tied (`A >= B`), seek a minimal both-and fix first or escalate under `## Decisions`.
1. **Handle lower-priority `P1`s**: fix when cheap and reversible; if a fix degrades a higher priority or expands scope materially, defer explicitly under `## Decisions` or `## Suggestions`.
1. **Prevent round-2 oscillation & log trade-offs**: on round 2, re-run only reviewers verifying fixed `P0`/`P1`s (never re-block on adjudicated overrides). Whenever `>= 2` reviewers collide or a verified `P0`/`P1` is downgraded, overruled, or deferred, include a compact `Trade-Offs` table in `## Context`:

```markdown
| Finding            | Lenses                   | Priority Rule          | Resolution                                 |
| ------------------ | ------------------------ | ---------------------- | ------------------------------------------ |
| <id / short issue> | `<lens A>` vs `<lens B>` | `<A > B or risk tier>` | `<fixed / both-and / deferred with rule:>` |
```
