---
name: system-prompts
description: "Design layered, cache-friendly system prompts, tool guardrails, and schema-validated outputs for LLM agents."
---

# System Prompts

[model-providers](../../model-providers/SKILL.md#request-contracts) owns per-model request parameters; [task-prompts](../../task-prompts/SKILL.md) owns coding-agent handoffs.

## Principles

- **Layer by stability**: place static system instructions and tool schemas first to maximize prefix caching, followed by per-turn context, conversation history, and user input (placing long documents before the question).
- **State each rule once, with its why**: drop `CAPS`, `MUST` walls, and legacy nudges (`"if in doubt, use the tool"`) that current Gemini and Claude models over-trigger ([Gemini prompting](https://aistudio.google.com/docs/prompting-strategies), [Claude prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
- **Require critical thinking and completeness**: instruct agents in positive terms to verify premises against grounded evidence, surface uncertainty rather than guessing, handle empty/boundary/failure cases, and finish deliverables end-to-end without shortcuts.
- **Enforce authority in code**: delimit retrieved text, tool outputs, and memory as untrusted data; gate permissions, spend, and destructive actions in runtime/tool code, never prompt-only.
- **Validate structured output and fail closed**: use native schemas (ADK `output_schema`, LangChain `response_format`, `google-genai` `response_schema`) with Pydantic validation; reject invalid payloads instead of repairing prose, and isolate prompt changes against [evaluation](evaluation/GUIDE.md).
