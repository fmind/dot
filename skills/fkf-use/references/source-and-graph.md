# Source and graph contracts

Read this reference when configuring collection, bodies, identities, or graph relations. The base's `AGENTS.md` remains authoritative when it is stricter.

## Data model

| Layer                              | Holds                                                           |
| ---------------------------------- | --------------------------------------------------------------- |
| `events/YYYY-MM-DD/`               | One complete JSON document per enabled event source.            |
| `index/`                           | One current document per index source.                          |
| `tasks/YYYY-MM-DD/<slug>/TASKS.md` | Requests, work, verification, and findings from one session.    |
| `projects/<slug>.md`               | Intent, status, decisions, open questions, and actionable work. |
| `wiki/<slug>.md`                   | Flat, tagged, reusable knowledge.                               |
| `graph*.tsv`                       | Rebuildable source, destination, and offset caches.             |

Root `schema:` owns shared field meanings, `one`/`optional`/`many` cardinality, and `relation: true`. Sources map provider paths to those fields; only `id` and event `time` are structural. Stored documents retain the schema subset and field map used to create them.

Root `identities:` and authored pages may merge exact aliases. FKF never infers identity or relations from prose, titles, field names, or matching values.

## Source execution

Prefer, in order:

1. direct provider argv in `run:`;
1. a reviewed `.sh` or `.py` helper under `bin/` for pipelines or expansion;
1. another executable for structured or stateful work.

`run:`, optional `test:`, `auth:`, and `body:` are direct argv. A helper's shebang chooses its interpreter. Declare every ordinary executable and non-standard interpreter in `requires:`. Source hooks live under `tests/`; FKF prepends that tree only for `test:` so fixtures cannot shadow collectors.

Placeholders use exact lowercase `{{name}}`. FKF supplies dates and paths as individual argv items and never reparses them through a shell. `body:` alone may name max-one fields already present in the stored map; option-like or invisible/control values are refused.

`auth:` is a bounded readiness probe. An ordinary non-zero provider exit marks the source login-required for that run; missing executables, timeouts, signals, unsafe paths, trust drift, and runner failures stay hard errors. Probe and provider output is never disclosed.

Every collector emits one complete JSON document. New records must project meaningful, control-free titles. A `window: true` source runs once per contiguous missing span. Preview runs and validates one source once, returns at most three projected samples, and writes nothing.

## Graph

Edges come only from:

1. stored fields declared `relation: true`;
1. authored Markdown links;
1. page tags;
1. declared relation fields under `relations:` frontmatter;
1. root `identities:` aliases;
1. `aliases:` on authored person or organization pages.

The two declared-alias forms emit auditable `same-as` edges from each alias to its canonical URI. FKF never infers those edges from matching names or values.

The graph is a digest-bound cache over exact documents and authored pages. Root rows are `src`, `dst`, `kind`, `at`, `via`, and `indexed`. Rebuild after source or authored changes; `graph --verify` hashes every input and artifact without writing.

For a neighbourhood, `--kind` filters edge kinds such as `participant`; for `graph nodes`, it filters node kinds such as the `person` entity scheme.

## Failure and concurrency

Collection is all-or-nothing per unit. Non-zero exit, timeout, excessive output, invalid or multiple JSON documents, or missing required values leaves that unit absent. Diagnostics name only reviewed source/window/argv context and never provider stderr or record-derived body arguments.

One writer lock covers every mutating path for the physical base, including symlink aliases. Do not retry around it. Readers, dry runs, previews, `trust --check`, and build checks are lock-free.
