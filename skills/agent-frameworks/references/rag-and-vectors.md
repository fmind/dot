---
name: rag-and-vectors
description: "Build hybrid pgvector/DuckDB retrieval with tenant ACL pushdown, Gemini embeddings, and native multimodal inputs."
---

# Retrieval & Vector Search

Use native Gemini 4 multimodal understanding before adding chunking/vector infrastructure; add Postgres `pgvector` or local DuckDB hybrid search when corpora exceed prompt budgets.

## Prefer Native Multimodal Before RAG

- **Skip unnecessary chunking**: Gemini 4 accepts PDFs, audio, video, Office (`.docx`, `.pptx`, `.xlsx`), and OpenDocument files natively inside 1M-token windows; pair with durable implicit prefix caching (`>= 4,096` tokens) when querying fixed document sets repeatedly ([gcp-agent-platform](../../model-providers/references/gcp-agent-platform.md)).

## Hybrid Retrieval (`pgvector>=0.8.0` + FTS + RRF)

- **Push ACL filters inside both CTEs with iterative scan**: enforce `WHERE tenant_id = $1 AND ...` in both vector and lexical arms before RRF scoring and set `SET LOCAL hnsw.iterative_scan = strict_order;` inside the transaction (`pgvector>=0.8.0`, or partition/partial-index per tenant on `<0.8`) so selective tenant filters do not truncate recall at `hnsw.ef_search`:
  ```sql
  SET LOCAL hnsw.iterative_scan = strict_order;
  WITH vec AS (
    SELECT id, row_number() OVER (ORDER BY embedding <=> $2::vector) AS r
    FROM chunks WHERE tenant_id = $1
    ORDER BY embedding <=> $2::vector LIMIT 40
  ),
  fts AS (
    SELECT id, row_number() OVER (ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', $3)) DESC) AS r
    FROM chunks WHERE tenant_id = $1 AND tsv @@ plainto_tsquery('english', $3)
    ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', $3)) DESC LIMIT 40
  )
  SELECT coalesce(vec.id, fts.id) AS id,
         coalesce(1.0 / (60 + vec.r), 0.0) + coalesce(1.0 / (60 + fts.r), 0.0) AS rrf_score
  FROM vec FULL OUTER JOIN fts ON vec.id = fts.id
  ORDER BY rrf_score DESC LIMIT 10;
  ```
- **Index & ground retrieval**: add `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` plus `GIN` on generated `tsvector`; delete stale chunks and resync ACL metadata on source updates, return `(source_id, updated_at)` provenance on every hit for citation grounding, and evaluate retrieval recall independently from final generation ([evaluation](evaluation/GUIDE.md)).

## Local Embedded Corpora (`duckdb>=2.0`)

- **Single-file hybrid search**: `INSTALL vss; LOAD vss; INSTALL fts; LOAD fts;` (enable `SET hnsw_enable_experimental_persistence = true` only when persisting HNSW indexes on disk in single-writer local tools, or scan exact cosine similarity on `< 100k` vectors). No separate vector service required.

## Gemini Embeddings (`google-genai>=3.3.0`)

- **Match `task_type` & reduced dimensions**: call `await client.aio.models.embed_content(model="gemini-embedding-001", contents=texts, config=types.EmbedContentConfig(output_dimensionality=768, task_type="RETRIEVAL_DOCUMENT"))` for indexing and `"RETRIEVAL_QUERY"` at query time; L2-normalize vectors when reducing dimensions cleanly before storage ([Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings)).

## Documentation

- [pgvector](https://github.com/pgvector/pgvector) · [pgvector Python](https://github.com/pgvector/pgvector-python) · [DuckDB VSS](https://duckdb.org/docs/stable/core_extensions/vss) · [DuckDB FTS](https://duckdb.org/docs/stable/core_extensions/full_text_search)
