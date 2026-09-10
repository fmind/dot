---
name: langextract
description: Extract grounded structured information with LangExtract. Use for few-shot extraction, source spans, provider configuration, JSONL output, and alignment failures.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/langextract
  created: "2026-09-10"
  updated: "2026-09-10"
---

# LangExtract

Use Google LangExtract for source-grounded text extraction; [pydantic](../pydantic/SKILL.md) owns output contracts and [agent-evaluation](../agent-evaluation/SKILL.md) owns measured extraction quality.

## Workflow

1. Inspect the installed API and select `langextract-usage` from upstream. Add `langextract` with `uv add langextract`, plus provider extras only when needed.
1. Define extraction classes and attributes, then construct `lx.data.ExampleData` with literal source spans in `Extraction.extraction_text`. Test examples with strict prompt alignment validation.
1. Configure the provider and model explicitly for the approved data destination and budget. Pass local text with URL fetching disabled (`fetch_urls=False`) unless remote retrieval is required and authorized.
1. Call `lx.extract` with a bounded chunk size, worker count, and initial single extraction pass. Use the pinned version's strict prompt validation options; fix mismatched examples rather than suppressing warnings.
1. Check every extraction's `char_interval` against the original text. Report unaligned results separately instead of silently counting them as grounded success; deduplicate repeated spans deliberately.
1. Save annotated documents with `lx.io.save_annotated_documents` and inspect `lx.visualize` output locally. Test empty text, repeated entities, overlapping spans, and provider failures; compare held-out precision/recall before increasing passes.

## Gotchas

- Source alignment establishes where text came from, not whether an inferred attribute is true.
- Example validation and runtime output validation are separate checks. Successful parsing does not prove all expected entities were found.
- JSONL and visualization artifacts retain source text; apply the source's privacy and retention rules. Increased passes and workers change cost and rate-limit behavior.

## Official Skills

Upstream: [google/langextract](https://github.com/google/langextract/tree/main/skills/langextract-usage), skill `langextract-usage`, with provider, resolver, and prompt-validation references. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) to review and install only the needed project-scoped selection.

## Documentation

- [Official project and API examples](https://github.com/google/langextract) · [Usage skill](https://github.com/google/langextract/tree/main/skills/langextract-usage)
