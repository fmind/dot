# Prompt Design Procedure

Read for the detailed campaign, protocol, or reporting requirements when the task needs them.

1. **Name the success contract**: user-visible behavior, failure semantics, forbidden actions, measurable acceptance criteria, and the cheapest development cases that separate success from failure; product ambiguity goes to [product-loop](../../product-loop/SKILL.md) first.
1. **Inspect the runtime input**: trace every layer in precedence order (provider rules, system and developer text, tenant customization, memory, tool schemas, retrieval, history, user input), note truncation and caching, and design against the runtime prompt, not a file.
1. **Pin the baseline**: code revision, prompt hash, assembly implementation, model version, tool and output schemas, retrieval snapshot, context limit, sampling, retries, and known results; separate prompt changes from system changes.
1. **Partition context by lifetime**: stable policy and tool contracts early and cacheable, tenant or session context in a bounded layer, volatile request state last; define precedence and deterministic truncation before the window fills.
1. **Write one behavioral contract**: each instruction in one authoritative place, stating goal, constraints, decision authority, success criteria, failure behavior, and output contract; cut persona flourishes, repeated rules, and speculative edge cases.
1. **Encode authority and autonomy**: what the agent may read, write, call, spend, send, or publish, which actions need confirmation, and when it must stop; conflicts resolve by explicit priority, never by recency or persuasive wording inside data.
1. **Design tool contracts**: unique action-oriented names, a concise purpose, and the field list in [tool contracts](tool-contracts.md); expose only the tools relevant to the task.
1. **Make outputs machine-checkable**: a typed schema or discriminated result variants with required fields, enums, nullability, evidence fields, and refusal or partial-success shapes; validate in code and fail closed.
1. **Choose examples at decision boundaries**: the fewest examples that resolve an ambiguous rule, output shape, tool choice, or refusal, including hard negatives; never copy sealed evaluation cases into the prompt.
1. **Harden dynamic insertion**: typed template parameters, explicit delimiters, length bounds, format-appropriate escaping, provenance labels, and deterministic placement; reject missing variables instead of emitting placeholders.
1. **Run static checks**: render the candidate with representative values and inspect it in final order for contradictions, unknown tools or fields, schema-invalid examples, unresolved variables, authority inversion, and rules the runtime cannot enforce.
1. **Hand off to evaluation**: diff and hash the baseline and candidate, state one change hypothesis with its guardrails, freeze the candidate, and deliver the [prompt candidate](prompt-candidate.md) to the project's bounded evaluation workflow for paired trials.

## Sources

- Adapted from [OpenAI prompting guidance](https://developers.openai.com/api/docs/guides/prompting), [OpenAI model optimization guidance](https://developers.openai.com/api/docs/guides/latest-model), [OpenAI Model Spec](https://model-spec.openai.com/2025-10-27), [Google prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies), [Anthropic prompt engineering](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview), [Anthropic jailbreak mitigations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks), [ECC prompt-optimizer at `59a99d6`](https://github.com/affaan-m/ECC/blob/59a99d669f5466d99d5be8b6fce8c5f2677766d0/skills/prompt-optimizer/SKILL.md).
