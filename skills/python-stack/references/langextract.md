---
name: langextract
description: "Extract structured facts from text with LangExtract and source-grounded evidence."
---

# LangExtract

Use Google LangExtract for source-grounded text extraction; [pydantic](pydantic.md) owns output contracts and [agent-evaluation](../../agent-evaluation/SKILL.md) owns measured extraction quality.

## Workflow

1. **Inspect the installed API first**: select `langextract-usage` from upstream. Add `langextract` with `uv add langextract`, plus provider extras only when needed.
1. **Ground examples in literal spans**: define extraction classes and attributes, then construct `lx.data.ExampleData` with literal source spans in `Extraction.extraction_text`. Test examples with strict prompt alignment validation.
1. **Configure the provider; never auto-fetch URLs**: configure the provider and model explicitly for the approved data destination and budget; for GCP Agent Platform pass `language_model_params={"vertexai": True, "project": ..., "location": "global"}` per [model-providers](../../model-providers/SKILL.md). LangExtract 1.7 treats every string as literal text (`fetch_urls` defaults to False); do not rely on URL fetching. When remote input is required and authorized, fetch it through the project's bounded, destination-validated HTTP client before extraction; LangExtract's built-in fetching does not establish an SSRF boundary.
1. **Bound extraction and surface omissions**: call `lx.extract` with a bounded chunk size, worker count, and initial single extraction pass. Use the pinned version's strict prompt validation options; fix mismatched examples rather than suppressing warnings. Check support for `resolver_params={"suppress_parse_errors": False}` and use it when incomplete extraction is a failure: the default can warn and omit malformed chunks. If partial extraction is intentional, track and report omitted chunks explicitly.
1. **Verify every span's alignment**: check every extraction's `char_interval` against the original text. Report unaligned results separately instead of silently counting them as grounded success; deduplicate repeated spans deliberately.
1. **Inspect and test before adding passes**: save annotated documents with `lx.io.save_annotated_documents` and inspect `lx.visualize` output locally. Test empty text, repeated entities, overlapping spans, and provider failures; compare held-out precision/recall before increasing passes.

## Gotchas

- **Alignment proves provenance, not truth**: source alignment establishes where text came from, not whether an inferred attribute is true.
- **Validate examples and outputs separately**: example validation and runtime output validation are separate checks. Successful parsing does not prove all expected entities were found.
- **Apply source privacy to artifacts**: JSONL and visualization artifacts retain source text; apply the source's privacy and retention rules. Increased passes and workers change cost and rate-limit behavior.

## Official Skills

Upstream: [google/langextract](https://github.com/google/langextract/tree/main/skills/langextract-usage), skill `langextract-usage`, with provider, resolver, and prompt-validation references. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) to review and install only the needed project-scoped selection.

## Documentation

- [Official project and API examples](https://github.com/google/langextract) · [Usage skill](https://github.com/google/langextract/tree/main/skills/langextract-usage)
- Releases: [LangExtract](https://github.com/google/langextract/releases)
