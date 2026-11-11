# Skill Adoption Check

Test substantial skill additions or routing changes on realistic tasks to verify automatic discovery and execution value.

1. **Define probes upfront**: pick a natural prompt (without naming the skill), a neighboring prompt that routes elsewhere, and an observable pass condition before running.
1. **Run in a fresh host session**: expose the candidate catalog and minimal fixtures; observe selected skills (explicit `/skill-name` tests execution, not discovery).
1. **Check artifacts, not claims**: verify files, exit codes, and side effects on an isolated task including its target failure boundary.
1. **Compare against baseline**: record success, corrections, extra steps, latency, and token/cost vs the prior workflow (one run is anecdotal; use [agent-evaluation](../../agent-evaluation/SKILL.md) for repeated stochastic trials).
1. **Report cleanly**: log host/model, catalog revision, selected skills, outcome, and unverified host boundaries in the task report, redacting private prompts. Keep trial fixtures out of the package (`check:skills` rejects `evals/`); judge description edits on held-out probes.
