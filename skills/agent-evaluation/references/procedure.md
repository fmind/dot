# Agent Evaluation Procedure

Read for the detailed campaign, protocol, or reporting requirements when the task needs them.

1. **State the decision**: name the evaluated unit, baseline, candidate, segments, primary metric, guardrails, and kill criterion.
1. **Pick the mode**: development mode (frozen cases, paired runs, deterministic graders) returns only `ITERATE` or `INCONCLUSIVE`; release or adoption mode adds a sealed holdout, a predeclared decision rule, blinded graders, and adequate repetitions.
1. **Pin candidate identity**: model provider and immutable version, prompts or their hashes, tool schemas, retrieval snapshot, code revision, sampling, retries, and grader versions; a model name alone is not identity.
1. **Build scenario sets**: a versioned development corpus from sanitized logs, incidents, and known failures that covers success paths, adversarial and refusal cases, tool errors, and long-tail segments; release mode adds a sealed, contamination-checked holdout.
1. **Capture traces**: final response plus tool calls, arguments, results, denials, retrieval sources, errors, tokens, latency, cost, and cleanup; grade attempted unsafe actions even when the gateway blocked them.
1. **Stack graders**: deterministic schema checks, executable tests, and trace assertions first; pairwise or criteria scoring for semantic dimensions; a blinded pinned model judge only where code cannot decide; humans for safety and disagreement.
1. **Calibrate and blind**: test graders on labeled passes, failures, and edge cases; give judges randomized opaque candidate labels, strip provider metadata, swap order, and report false positives, false negatives, and blind spots. A candidate never grades itself.
1. **Justify trial counts**: choose trials, seeds, minimum detectable difference, and uncertainty method before running, per the [evaluation protocol](references/evaluation-protocol.md); return `INCONCLUSIVE` when the count cannot separate the threshold.
1. **Run paired comparisons**: baseline and candidate on identical cases, tools, budgets, and fresh state; retain every valid run, failure, timeout, and grader disagreement.
1. **Analyze by risk and segment**: report capability, reliability, safety, latency, tokens, and cost separately; an aggregate gain never hides a safety regression or a minority-segment loss.
1. **Spend the holdout once**: Freeze the decision rule before the sealed holdout, keep an append-only exposure log, run the frozen candidate on it once, record the corpus hash, and rotate an exposed holdout.
1. **Make the call**: return `ADOPT`, `ITERATE`, `REJECT`, or `INCONCLUSIVE` tied to the predeclared thresholds, with the cheapest next evidence, in the [evaluation brief](references/evaluation-protocol.md#evaluation-brief) shape.

## Sources

- Adapted from [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [ECC eval-harness at `59a99d6`](https://github.com/affaan-m/ECC/blob/59a99d669f5466d99d5be8b6fce8c5f2677766d0/skills/eval-harness/SKILL.md), [Anthropic skill-creator at `f17010c`](https://github.com/anthropics/skills/blob/f17010c9bb483898c1d9c9f42dde2b3a98889434/skills/skill-creator/SKILL.md), [Awesome Copilot eval-driven-dev at `ab7544d`](https://github.com/github/awesome-copilot/blob/ab7544d03d4c49fdd07f5958e1888ad39c4118e2/skills/eval-driven-dev/SKILL.md), [gstack benchmark-models at `960c3a8`](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/benchmark-models/SKILL.md).
