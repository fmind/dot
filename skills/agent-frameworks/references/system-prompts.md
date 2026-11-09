---
name: system-prompts
description: "Application system prompt layering, rule wording, and validated structured output."
---

# System Prompts

Layer the instructions of an agent or embedded LLM call so the model sees one rule per concern and the runtime enforces the rest. [model-providers](../../model-providers/SKILL.md#request-contracts) owns per-model request contracts (sampling, prefill, tool choice, stable prefix); [task-prompts](../../task-prompts/SKILL.md) owns handoff prompts for coding agents.

1. **Layer by stability**: system text and tool definitions first, then per-turn context (date, memory, retrieval), history, and user input; put long documents before the question.
1. **Write each rule once, with its reason**: one layer owns each rule; state what to do and why, and drop CAPS, MUST, and older-model compensations such as "if in doubt, use the tool", which current Claude and Gemini models over-apply.
1. **Keep authority in code**: delimit retrieved text, tool results, and memory as data; authorization, spending limits, and destructive-action gates live in tools and runtime code, never only in the prompt.
1. **Validate structured output in code and fail closed**: request native structured output (ADK `output_schema`, LangChain `response_format`, google-genai `response_schema`), validate it with Pydantic, and reject a missing or invalid field instead of repairing free text. Ask for the decision, a short rationale, and evidence, not written-out reasoning.
1. **Change only the prompt when comparing**: keep model, tools, retrieval, and effort fixed between baseline and candidate, keep evaluation cases out of the examples, and compare with [agent-evaluation](../../agent-evaluation/SKILL.md).

## Documentation

- [Google prompt design](https://ai.google.dev/gemini-api/docs/prompting-strategies) · [Anthropic prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
