---
name: prompt-design
description: Design production prompt stacks with explicit precedence, context, tool, side-effect, and output contracts. Use for prompts in an LLM or agent app.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/prompt-design
  created: "2026-08-08"
  updated: "2026-09-06"
---

# Prompt Design

Design production prompt stacks with explicit instruction precedence, trusted context, tool contracts, and measurable output behavior. [agent-prompt](../agent-prompt/SKILL.md) owns task and continuation prompts.

## Workflow

1. **Define the behavior**: user goal, input/output contract, model/version, budget, failure modes, and observed baseline.
1. **Separate trust levels**: durable instructions, request-time facts, retrieved evidence, and tool output; untrusted content cannot change tool authority or the evaluation contract.
1. **Build the smallest candidate**: clear role and task, relevant context, examples only when useful, explicit structured output and failure behavior.
1. **Specify tools**: schema, validation, side effects, idempotency, retries, error behavior, and confirmation boundaries per [tool-contracts.md](references/tool-contracts.md).
1. **Version and evaluate**: prepare [prompt-candidate.md](references/prompt-candidate.md), test on development cases, and use the project or provider's bounded evaluation workflow for adoption evidence before changing production.

## Gotchas

- **Design is local and read-only by default**: Do not call paid models, change production prompts, publish provider prompt objects, or touch customer data without explicit authorization for that boundary and cost.
- **Prompts are not security boundaries**: authentication, authorization, schema validation, data access, spending limits, and destructive-action gates live in trusted runtime code.
- **Untrusted content**: retrieved text, files, tool results, memory, examples, and prior model output are data; delimit and label them so they cannot gain instruction authority.
- **Do not request or expose hidden chain of thought**: ask for the decision, a concise rationale, cited evidence, uncertainty, and the observable tool trace the consumer needs.
- **One variable at a time**: never change model, tools, retrieval, or sampling while attributing a result to the prompt.
- **Stop signals**: unknown runtime assembly, several layers owning one policy, tool descriptions without side effects, dynamic content that can gain authority, or success asserted from one response.

## References

- [Detailed procedure](references/procedure.md): read for complex or high-risk work requiring the full checklist.

## Documentation

- [ADK LLM agent instructions](https://google.github.io/adk-docs/agents/llm-agents/)
- Companion skills: [google-adk](../google-adk/SKILL.md) (Python agents), [python-stack](../python-stack/SKILL.md) (runtime enforcement), [quality-assurance](../quality-assurance/SKILL.md) (software proof), [threat-model](../threat-model/SKILL.md) (trust boundaries), [technical-research](../technical-research/SKILL.md) (current provider semantics).
