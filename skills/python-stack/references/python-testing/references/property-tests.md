# Property Tests

Add Hypothesis (`uv add --group <test-group> hypothesis`) only when parsers, codecs, or stateful sequences need generated input coverage.

- **CI profile**: setting `CI` activates Hypothesis's built-in `ci` profile (derandomized, no example DB/deadline, prints `@reproduce_failure(...)` blobs — replay locally on the same Hypothesis version, then remove the decorator).
- **State & `@example(...)`**: promote real counterexamples to `@example(...)`, and reset mutable state inside each test body (function-scoped pytest fixtures run once per test, not per generated example).
- **Security invariants**: generate multi-principal sequences asserting tenant isolation and rejected-credential denial alongside authorized successes (so deny-all implementations still fail).

Sources: [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html) · [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) · [settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#settings).
