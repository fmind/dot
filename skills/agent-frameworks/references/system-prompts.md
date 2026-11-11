---
name: system-prompts
description: "Application system prompt layering, rule wording, and validated structured output."
---

# System Prompts

Layer application prompts so each concern has one rule and code enforces boundaries. [model-providers](../../model-providers/SKILL.md#request-contracts) owns per-model request contracts; [task-prompts](../../task-prompts/SKILL.md) owns coding-agent handoffs.

1. **Layer by stability**: static system text and tool schemas first, then per-turn context (date, memory, retrieval), history, and user input, placing long documents before the question.
1. **State each rule once, with its why**: drop CAPS, MUST, and legacy nudges like "if in doubt, use the tool" that current Claude and Gemini models over-trigger.
1. **Enforce authority in code**: delimit retrieved text, tool outputs, and memory as untrusted data; gate permissions, spend, and destructive actions in runtime/tool code, never prompt-only.
1. **Validate structured output and fail closed**: use native schemas (ADK `output_schema`, LangChain `response_format`, google-genai `response_schema`) with Pydantic validation; reject invalid payloads instead of repairing prose, and request decision, brief rationale, and evidence rather than chain-of-thought text.
1. **Isolate prompt changes**: hold model, tools, retrieval, and effort constant, exclude eval cases from examples, and grade with [agent-evaluation](../../agent-evaluation/SKILL.md).

## Documentation

- [Google prompt design](https://ai.google.dev/gemini-api/docs/prompting-strategies) · [Anthropic prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
