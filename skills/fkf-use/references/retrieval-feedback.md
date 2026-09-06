# Turn a retrieval miss into a regression case

Use this only when the user reports incorrect, missing, or irrelevant retrieval and authorizes retaining the example. The user owns the expected answer; inferred relevance is a proposal for review.

1. Record the selected base, original question, date window, delivery format, budget, and receipt digest if available. Remove secrets and unnecessary personal details before retaining anything.
1. Read the expected URI and confirm that it exists and supports the intended answer. Distinguish missing collection, stale evidence, a poor query, ranking, and output-budget loss.
1. Add one reviewed query under the existing `evals/queries.yaml` `queries:` list. Match the consumer's format and budget; name incorrect evidence in `forbidden_uris` when relevant.
1. Run `fkf --base <selected-base> eval`. Preserve a failing result until the underlying problem is fixed. Keep the original assertion when testing a candidate change.
1. Treat this exposed example as a development regression. Use fresh cases and comparable repeated agent trials before claiming a general improvement.

```yaml
- name: resume-project-constraint
  question: Resume the project without losing the accepted storage constraint
  k: 3
  budget: 850
  delivery: text
  window: { since: 2026-09-01, until: 2026-09-05 }
  expected_uris: [projects/example.md]
  forbidden_uris: [projects/unrelated.md]
```

Replace the illustrative question, dates, and URIs with the reviewed example. Do not copy this template unchanged into an acceptance set. A genuine absent-answer case uses `expect_empty: true` with no expected URIs. No separate feedback database, automatic transcript capture, or new command is needed.
