# Property Tests

Use Hypothesis (`uv add --group <test-group> hypothesis`) as the primary correctness multiplier on parsers, codecs, normalizers, schedulers, and stateful workflows—higher ROI than external formal provers because properties execute directly against deployed Python types.

- **Core invariant patterns**: assert lossless round-trips (`decode(encode(x)) == x`), idempotence (`normalize(normalize(x)) == normalize(x)`), metamorphic invariants (sorting/reordering inputs preserves set outputs), and reference-oracle equivalence against a trivial slow implementation.
- **CI profile**: setting `CI` activates Hypothesis's built-in `ci` profile (derandomized, no example DB/deadline, prints `@reproduce_failure(...)` blobs — replay locally on the same Hypothesis version, then remove the decorator).
- **State & `@example(...)`**: promote real counterexamples to `@example(...)`, and reset mutable state inside each test body (function-scoped pytest fixtures run once per test, not per generated example); use `RuleBasedStateMachine` for multi-step repository/cache/queue invariants.
- **Security & policy equivalence**: generate multi-principal sequences asserting tenant isolation and rejected-credential denial alongside authorized successes (so deny-all implementations still fail); add `z3-solver` per project only when proving exhaustive IAM, CIDR, or guardrail rule equivalence across symbolic domains.

Sources: [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html) · [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) · [settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#settings) · [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html).
