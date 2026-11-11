---
name: langextract
description: "Extract structured facts from text with LangExtract and source-grounded evidence."
---

# LangExtract

Source-grounded structured extraction with Google LangExtract; [pydantic](pydantic.md) owns schemas and [evaluation](../../agent-frameworks/references/evaluation/GUIDE.md) owns precision/recall evaluation.

## Workflow

1. **Inspect API & install**: consult installed `langextract-usage` or `.venv/` source; install `uv add langextract` (plus provider extras only when needed).
1. **Literal span examples**: build `lx.data.ExampleData` with verbatim `Extraction.extraction_text` spans, and pass `prompt_validation_level=PromptValidationLevel.ERROR` (`langextract.prompt_validation`) + `prompt_validation_strict=True` to `lx.extract` (fix examples rather than relaxing validation).
1. **Explicit provider, no URL auto-fetch**: set approved provider/model (`language_model_params={"vertexai": True, "project": ..., "location": "global"}` per [model-providers](../../model-providers/SKILL.md)). Keep `fetch_urls=False` (LangExtract `1.7` default; built-in fetching has no SSRF guard — fetch authorized remote text beforehand via a bounded HTTP client).
1. **Bound & surface parse errors**: set `max_char_buffer`, `max_workers`, `extraction_passes=1`, and `resolver_params={"suppress_parse_errors": False}` when dropped chunks are errors (default warns and drops malformed chunks).
1. **Check alignment & test**: verify `char_interval` and `alignment_status` (report missing/`!= MATCH_EXACT` separately and deduplicate spans); inspect via `lx.io.save_annotated_documents` + `lx.visualize`, and measure held-out precision/recall before raising `extraction_passes`.

## Gotchas & Upstream Skill

- **Alignment != factual truth** (proves span provenance only); example validation != recall completeness; JSONL/HTML outputs retain source text (apply source privacy rules).
- Upstream: [google/langextract](https://github.com/google/langextract) ([langextract-usage](https://github.com/google/langextract/tree/main/skills/langextract-usage), install per [vendor-skills](../../agent-project/references/vendor-skills.md)) · [Releases](https://github.com/google/langextract/releases).
