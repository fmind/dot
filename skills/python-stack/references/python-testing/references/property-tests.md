# Property Tests

Use Hypothesis when a broad input space or operation sequence makes example-only coverage weak; do not add it to every project by default.

- **Keep Hypothesis a test dependency**: reuse existing configuration; otherwise add it with `uv add --group <test-group> hypothesis` and run it through the existing pytest task.
- **Know the CI profile**: when `CI` is set, Hypothesis loads its built-in `ci` profile (derandomized, no example database or deadline, failure blobs printed), so CI never replays the local database. Replay a CI failure locally with its printed `@reproduce_failure(...)`, then remove it: blobs hold only for the same Hypothesis version.
- **Keep real counterexamples as `@example(...)` regressions** when they explain a real defect, and reset mutable state per example: a function-scoped fixture is not recreated for each generated example.
- **Constrain authority in security properties**: generate sequences with distinct principals and assert that tenant A never changes tenant B's state and rejected credentials never authorize an operation; keep authorized successes in the suite so a deny-everything implementation cannot pass.

Sources: [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html), [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html), and [settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#settings).
