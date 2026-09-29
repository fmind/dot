---
name: retrieval
description: "Read pages, search within a scope, follow paginated replies and text pages, and check graph claims and coverage."
---

# Complete reads and graph context

<!-- Mirrors github.com/fmind/brain-framework src/bf/skills/bf-use/references/retrieval.md (v16.1.0); update it there first. -->

Helpers named `skills/bf-use/scripts/…` belong to the packaged skill: run them from a brain that installed it with `bf skills skills`, or from the host folder where `bf skills DIR` put it.

Use when a reply is paged, a graph claim matters, a review needs source coverage or an answer must be complete. The [retrieval reference](https://fmind.github.io/brain-framework/docs/retrieval/) owns the exact contract.

## Continue a result

Keep the query or page ref, scope, limit and brain selection unchanged and set `--offset` to the reply's `next_offset`; stop when it is absent. A page or preview is not the complete result. Restart when evidence changes during the walk.

An exact read above 32 KiB returns its text in pages. A note's first page carries its backlinks, claims, an `outline` of `#section` refs with their `characters`, and only the first 4 KiB of text: read the section the task needs by its ref. To assemble the whole text instead, repeat the same read with each `next_offset` and join the `text` (or `record.text`) slices; every page names the file's `sha256`, so restart if it changes. Offsets count Unicode characters. `python3 skills/bf-use/scripts/evidence.py read REF --brain PATH` does this and checks the digest.

Quote refs in shell commands. A `#` inside a record ID is part of its identity; a note section ref uses the heading slug or explicit `{#id}` after `.md`. With several selected brains, entries name their `brain` and `uri`, and a plain ref present in two brains fails: read the `uri` instead. MCP `read` takes `ref`, `rel` and `offset`; choose a brain with a `bf://NAME/` address.

## Search precisely

Search matches words case-, accent- and compatibility-insensitively. It ignores English and French function words when other words remain, and every distinct word after the first 32. Any word matches; a passage matching more of the query ranks higher, a section also ranks by its note's title, its heading and the note's tags, and equal scores list the newest first. A nested section's title reads `Note — Parent — Child`.

- `"quoted phrase"` matches the words in order; `word*` matches every word starting with `word`.
- `unmatched` lists query words, phrases or prefixes found nowhere in the selected brains, whatever the scope: respell them or search a variant.
- A result's `sections` names up to 3 other matching sections of the same note; `also` names other sources' records sharing its URL.
- An identity-shaped query, such as `repo:github.com/owner/name`, lists the owning note and the items linking to it; `"identity":"unknown"` means nothing in the cache names it.
- Records of a `priority: low` source rank at half weight. Unspaced Chinese, Japanese or Thai text matches only as a whole run. A query without any word, such as `!!!`, exits 2.

A `--scope` takes one folder (`projects`, `memories/gmail`), period (`today`, `7d`, `2026-09`, `2026-09-21..2026-09-25`), identity or tag page (`bf://NAME/tags/LABEL`); a `memories/SOURCE` that no selected brain knows fails.

## Check coverage

Inspect `problems`, `stale` and `sources` before interpreting a result. Each problem has an `error` and, when known, its `brain` and `file`. `stale` names brains whose reply came from the cache while a writer was updating it: retry shortly. Search lists the sources of returned records and those that failed or are `overdue` or `never` collected; `sources_omitted` counts the others, and an empty reply or a `memories` scope lists every searched source. Each source states its `state` (`active`, `disabled` or `historical`: records kept for a sensor no longer configured), `freshness` (`fresh`, `overdue`, `never`, `manual` or `unknown`), `last_collected`, `window` and `failed`. A fresh cache does not establish fresh provider evidence; an incomplete empty result does not prove absence.

Search and read refresh the brain's `.bf/` cache, so a read-only brain fails with a write-access error: grant access or use a copy.

## Follow the graph

A whole note, record or identity read includes `backlinks` grouped by `relation` (`links` for untyped links, `cites` for OKF sources). Each group previews its 5 newest items with their `title`, `date` or `time`, a 160-character `excerpt` and declared single-value `fields`; when `total` exceeds the preview, `bf read 'REF' --rel RELATION` lists every item, following `next_offset`. That relation page takes a whole note, record or identity, never a section; `--rel PARENT` also lists the items of relations declaring it as `broader`.

`claims` lists what the read item states, each with its `relation`, `target`, `origin` (the section or record making it) and the origin's `date` or `time`; outgoing claims keep up to 20 per relation and 50 in all, marked by `claims_truncated`. `bf search 'IDENTITY'` gives each linking item's `relations` (check `relations_truncated`). Section reads omit graph context: read the parent note for dependency review.

`bf read 'bf://NAME/'` opens another selected brain's home page; `bf://NAME/tasks`, `bf://NAME/7d` and `bf://NAME/tags/LABEL` open its pages. Pages own that namespace: no entity or alias can claim it.

For analysis outside BF, `bf export` streams one JSON line per edge of the selected brains (`subject`, `relation`, `target`, `origin`, and `date` or `time`), and `bf export --kind identities` lists each note or record with every name it answers to. Both read the cache offline and exit 1 when evidence was skipped.

## Interpret attention signals

The home page's `attention` lists scheduled sensors and routines that failed or are overdue. Project entries add `modified` (the file's last change), `review_due` (the local day a review falls due), `review_source` and `review_reasons`; the [review guide](https://github.com/fmind/brain-framework/blob/v16.1.0/src/bf/skills/bf-use/references/review.md) says when a note falls due. A reminder, an edit or a new backlink is a reason to inspect, never evidence of verification.

`bf read tasks` lists open checkboxes in projects, concepts and `ACTION.md` notes; only `deprecated` closes a note's tasks, and `index.md`, `log.md` and action attachments are excluded. Period pages separate items dated in the period (`items`, `total`) from items modified in it (`changed`). A `priority: low` source appears on period and home pages only as a count with its `page`; read that page to list its records.
