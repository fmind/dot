# Property Tests

Use generated cases when a broad input space or operation sequence makes example-only coverage weak. Keep ordinary examples for the public contract and discovered regressions; do not add Hypothesis to every project by default.

1. State a domain invariant and a plausible implementation error it would detect. Avoid duplicating the algorithm as the test oracle.
1. Reuse existing Hypothesis configuration; if absent and justified, add it to the project's test dependency group with `uv add --group <test-group> hypothesis`, then run through the existing pytest task. Do not add a global runtime dependency.
1. Generate valid data by construction using bounded strategies. Use separate invalid-input strategies; excessive filtering hides missing coverage and can trigger health checks.
1. Exercise the actual parser, codec, migration, or state machine against an independent observable invariant. Introduce a small relevant fault in isolation to verify the property detects it before trusting the test.
1. Retain the minimized counterexample as an explicit regression when it explains a real defect. Record the Hypothesis/runtime versions and use its failure replay mechanism for investigation; a seed alone is not a permanent cross-version guarantee.

| Boundary | Useful property | Additional evidence needed |
| --- | --- | --- |
| Codec | Decoding an encoded supported value preserves its declared meaning | Fixed wire-format examples: encoder and decoder can share the same defect |
| Parser | Valid generated documents parse; malformed variants fail with the declared error | Unicode separators, empty fields, size bounds, and explicit expected values |
| Migration | A second invocation changes nothing; interrupted/resumed output equals uninterrupted output | Independent counts/relationships and old-version fixture read-back |
| State machine | Every permitted action sequence preserves the invariant; forbidden transitions are rejected | A simple independent model, isolated state, and realistic stop/retry paths |

For a JSON-shaped domain, build a bounded strategy from `none()`, `booleans()`, domain-sized `integers()`, finite `floats(allow_nan=False, allow_infinity=False)`, and `text()`; combine with `recursive`, `lists`, and `dictionaries` only to the depth the application supports. Generate Unicode rather than restricting to ASCII unless the contract requires it. If NaN or non-string keys are supported, define their comparison and serialization semantics explicitly.

For stateful behavior, use `RuleBasedStateMachine` with rules, preconditions, and invariants when it is simpler than hand-built sequences. Create mutable resources per example or reset them between examples; a function-scoped pytest fixture is not automatically recreated for every generated example.

Keep default health checks active and bound fixture work. Diagnose deadline failures instead of disabling deadlines to conceal a slowdown; an intentionally slow integration property needs an explicit, justified test profile. Never equate more examples with complete proof.

For a shrunk failure, check the input against the documented domain before changing production code. Distinguish a violated guarantee, an invalid generator, an incorrect property, and an unspecified contract. Fix the generator or property only with contract evidence; preserve a real counterexample rather than filtering it out. A function name alone is insufficient evidence for an algebraic guarantee.

Security properties should constrain authority as well as return values: actions by tenant A never change tenant B's state; rejected credentials never authorize an operation; a cancelled operation cannot acquire new authority. Generate sequences with distinct principals and reset state per example. Keep successful authorized actions in the suite so a deny-everything implementation cannot pass.

Sources: [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html), [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html), and [settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#settings).
