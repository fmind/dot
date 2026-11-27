# Request Contracts

Shared model tiers and cross-provider request invariants for [agent-frameworks](../SKILL.md). Always verify live IDs from the target provider catalog (`agy models` for `agy` CLI), never memory.

## Model tiers

| Tier     | Model IDs                                   |                              Pricing (1M in/out) | Thinking levels                               | Notes                                                                        |
| -------- | ------------------------------------------- | -----------------------------------------------: | --------------------------------------------- | ---------------------------------------------------------------------------- |
| Default  | `gemini-4-hydrogen`                         |                                  `$1.50 / $7.50` | `LOW`, `MEDIUM`, `HIGH` (def), `XHIGH`        | Everyday coding, agents, tool calls                                          |
| Step-up  | `gemini-4-neon`                             |                                 `$3.00 / $15.00` | `LOW`, `MEDIUM`, `HIGH` (def), `XHIGH`        | GA 2026-11-18; verified enterprise on Agent Platform (no Deferred/free tier) |
| Frontier | `gemini-4-carbon`, `gemini-4-argon`         | Carbon `$2/$10` (thru 2026-11-30; then `$4/$20`) | `LOW`, `MEDIUM` (def), `HIGH`                 | Hard reasoning, architecture, security (`argon` supports Deferred)           |
| Bulk     | `gemini-3.8-flash`, `gemini-3.5-flash-lite` |                 `$0.75 / $3.75`, `$0.30 / $2.50` | Flash: `LOW`/`MEDIUM`/`HIGH`; Lite: `MINIMAL` | High-volume extraction (Lite: 1M in / 64K out)                               |

## Cross-provider contracts

- **Gemini 4 (`Hydrogen`, `Neon`, `Argon`, `Carbon`)**:
  - Unified `1,048,576` input+output window with `65,536` foreground output segment (`32,768` non-streaming on Carbon); use `v1beta1` `continuation_token` or Interactions API `background=true` for longer decodes.
  - Set `thinking_level` only (`MINIMAL` and `thinking_budget` return HTTP 400); custom `temperature`/`top_p`/`top_k` are ignored.
  - Implicit durable caching applies at `>= 4,096` tokens (explicit caching unsupported; TTL controls start Jan 12, 2027); accepts native Office (`.docx`/`.dotx`/`.doc`/`.pptx`/`.ppt`/`.xlsx`/`.xls`) and OpenDocument (`.odt`/`.odp`/`.ods`) inputs.
- **Claude 5.x (`Opus 5.5`, `Sonnet 5.5`, `Haiku 5.5`, `Fable 5.2`)**: omit sampling params and trailing assistant prefills (HTTP 400). Keep `tool_choice: {"type": "auto"}` with `strict: true` (HTTP 400 on `any` or named tool). Keep system/tool prefixes byte-stable (`cache_control: {"type": "ephemeral"}`) and turns append-only (mutating prior turns invalidates thinking blocks with HTTP 400).
- **OpenAI (`Responses API`)**: omit legacy `chat.completions` for new reasoning or structured workloads; use `text_format`, `reasoning={"effort": ...}`, `strict: true`, `store=False` by default, and fail closed when `output_parsed is None`.

## Catalog references

- [Agent Platform models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models) · [Gemini choosing a model](https://aistudio.google.com/docs/choosing-a-model) · [Anthropic models](https://platform.claude.com/docs/en/models/overview) · [OpenAI models](https://developers.openai.com/api/docs/models)
