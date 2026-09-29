---
name: retrieval
description: "Read pages, search within a scope, follow paginated replies and text pages, and check graph claims and coverage."
---

# Read pages, search and read

<!-- Mirrors github.com/fmind/brain-framework skills/bf-use (v15.0.0); update it there first. -->

```bash
bf read                                        # home: projects due for review, recent actions and changes, activity, coming week, attention
bf read projects                               # project notes, deprecated last, with open task counts and the next task
bf read tasks                                  # open checkboxes in projects, concepts and actions
bf read today                                  # a day's items (also yesterday, 2026-09-25, 2026-09, 7d)
bf read memories/google-gmail-emails/7d        # one source's records in a period
bf read 'repo:github.com/owner/name'           # an identity: its owning note, 5 backlinks per relationship, claims
bf read projects/brain.md --rel part-of        # every item linking with one relationship (links: untyped, cites: sources)
bf search "retention decision"                 # words; fuller matches first
bf search "invoice" --scope memories/google-gmail-emails   # a folder, period, identity or bf://NAME/tags/LABEL
bf read 'projects/brain.md#next-actions'       # one section of a note
```

## Search and read

1. Start from a page for a situation ("what should I look at", "what happened", active work) and search for a subject with short subject words or an explicit identity. Reformulate a miss with other words; a longer sentence broadens word matches. A query without any word or identity (`!!!`) exits 2, and an unknown `memories/SOURCE` scope fails.
1. Inspect `problems` (objects with `error` and optional `brain` and `file`), `stale` and source coverage: `sources` lists returned records' sources and those that failed or are `stale` or `never` collected, and `sources_omitted` counts the rest; replies without items and `memories` scopes list every searched source, including those with zero matches. An incomplete empty answer does not prove absence, and a fresh cache does not prove fresh provider evidence.
1. Continue with the same query or ref, scope, limit and brain selection, setting `--offset` to `next_offset` until it is absent. Restart if evidence changes. A page or preview is not the complete result.
1. Read and cite the refs you rely on. Preserve refs literally and quote them in shell commands: a `#` inside a record ID is part of its identity, while note section refs put the heading anchor after `.md`. With several selected brains, results alternate by each brain's rank, and a plain ref present in two brains fails with exit 1: read the returned `uri` instead. Results show one record per URL across sources, listing the others under `also`; titles are 200-character previews. MCP `read` takes `ref`, `rel` and `offset`; select a brain with a `bf://NAME/` address.
1. Exact reads carry the file's `sha256` and `modified`. Above 32 KiB, the note's `text` or a record's `record.text` arrives in pages: the first page adds the context and an `outline` of section refs, later pages only text. Prefer reading the section you need; otherwise repeat the read with each `next_offset`, concatenate the text and restart if `sha256` changes. Offsets count Unicode characters, not bytes. See the [retrieval contract](https://fmind.github.io/brain-framework/docs/retrieval/#continuations).

## Graph context

A whole note or record read includes `backlinks` grouped by `relation` (`links` for untyped links, `cites` for OKF `sources`), each previewing its 5 newest items with its `total`, and `claims` whose explicit subject is the read item, with the asserting item's `time`. Check `claims_truncated`. List a whole group with `bf read REF --rel ROLE` (50 per page; a declared `broader` parent also lists its narrower roles, each item naming its own `relation`), and explain a link with `bf search 'IDENTITY'`, whose items carry `relations` with their `origin`. Section reads omit graph context: read the parent for dependency review.

`bf read IDENTITY` returns its owning note, or the items linking to it when none owns it, and `--scope IDENTITY` searches that owning note plus those items. `bf read 'bf://NAME/'` is that brain's home page; `bf://NAME/tasks`, `bf://NAME/7d` and `bf://NAME/tags/LABEL` open pages. Links never add another brain or contact a network. Ambiguous aliases fail visibly; never infer a relationship from similar names or prose.

## Attention and freshness

Project entries carry `modified`, `review_due`, `review` and `review_reasons`: 14 days after local file modification by default, or `review_after` days or an explicit `review_due` date; newer linked items appear under `new_links`. A reminder is a reason to inspect, not verification, and copies or checkouts reset file times. Only `deprecated` closes a note: it ranks last and leaves home, tasks and reminders, while `draft` and `stable` notes stay open. Period pages separate items dated in the period (`items`, `total`) from items modified in it (`changed`); future periods and home `upcoming` come from agenda sources. Records of `priority: low` sources appear there only as counts under `sources` or `activity`; read `memories/SOURCE/PERIOD` to list them.

Records are snapshots from their collection time: verify volatile facts (dates, owners, status) against the live source when the task authorizes it, and say when data may be stale. Search and read never collect; report the gap when newer evidence is needed. They refresh `.bf/`, so a read-only brain fails with a write-access error, or appears in `problems` with its `brain` when several are selected.
