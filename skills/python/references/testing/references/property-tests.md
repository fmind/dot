# Property Tests & Verification Ladder

Escalate verification depth to match blast radius instead of jumping straight to external theorem provers—Python-native properties execute directly against deployed types and code.

## Verification Ladder

| Tier                           | Tools (Project-Local)                                                                                        | Target Scope                                                                 |
| :----------------------------- | :----------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------- |
| **1. Baseline**                | `ty`, Pydantic, Ruff, `pytest` (branch coverage); opt-in: `diff-cover`, `import-linter`, `ast-grep` (`mise`) | Every repository; fast local/CI gate.                                        |
| **2. Behavioral & Fuzzing**    | `hypothesis` (`@given`, `RuleBasedStateMachine`), `schemathesis`, scoped `mutmut`                            | Parsers, codecs, state transitions, ASGI APIs, core domain logic.            |
| **3. Symbolic & Policy Proof** | `hypothesis-crosshair` (Z3 on Python), `z3-solver`                                                           | Authz/IAM/RBAC rules, pricing/billing math, narrow security guards.          |
| **4. Formal Design Model**     | **Quint** (modern TLA+, `npm`/`mise`) — see [adr-rfc.md](../../../../docs/references/adr-rfc.md)             | Distributed protocols, sagas, consensus, or locking _designs_ before coding. |

- **Skip Lean 4 for standard Python**: proving a separate Lean 4 model does not prove CPython implementation parity and adds heavy proof-maintenance drift; reserve interactive theorem provers for cryptographic primitives or verifiable policy kernels compiled from the prover itself.

## Hypothesis, Symbolic Execution & Fuzzing

Use Hypothesis (`uv add --group <test-group> hypothesis`) as the primary Tier 2 correctness multiplier on parsers, codecs, normalizers, schedulers, and stateful workflows:

- **Core invariant patterns**: assert lossless round-trips (`decode(encode(x)) == x`), idempotence (`normalize(normalize(x)) == normalize(x)`), metamorphic invariants (sorting/reordering inputs preserves set outputs), and reference-oracle equivalence against a trivial slow implementation.
- **CI profile**: setting `CI` activates Hypothesis's built-in `ci` profile (derandomized, no example DB/deadline, prints `@reproduce_failure(...)` blobs — replay locally on the same Hypothesis version, then remove the decorator).
- **State & `@example(...)`**: promote real counterexamples to `@example(...)`, and reset mutable state inside each test body (function-scoped pytest fixtures run once per test, not per generated example); use `RuleBasedStateMachine` for multi-step repository/cache/queue invariants.
- **Security & policy equivalence**: generate multi-principal sequences asserting tenant isolation and rejected-credential denial alongside authorized successes (so deny-all implementations still fail); add `z3-solver` per project only when proving exhaustive IAM, CIDR, or guardrail rule equivalence across symbolic domains.
- **Symbolic execution probe (`hypothesis-crosshair`)**: on pure parsers, authz checks, or numeric/policy logic where random generation misses narrow branches, add `hypothesis-crosshair` (Python 3.14-compatible) and run existing `@given` tests through CrossHair's Z3 backend via `@settings(backend="crosshair")` or a registered profile (`settings.register_profile("crosshair", backend="crosshair")` + `pytest --hypothesis-profile=crosshair`). Keep symbolic runs opt-in outside fast PR gates.
- **Stateful ASGI API fuzzing (`schemathesis` 4.x)**: for Litestar or FastAPI services, add `schemathesis` and test contracts in-process against the ASGI app without starting a server (`schema = schemathesis.openapi.from_asgi("/schema/openapi.json", app)` for Litestar, `"/openapi.json"` for FastAPI): use `@schema.parametrize()` with `case.call_and_validate()` for endpoint schema/500 checks, and subclass `class APIWorkflow(schema.as_state_machine()):` (overriding `before_call(self, case)` for auth injection) with `TestAPIWorkflow = APIWorkflow.TestCase` to fuzz multi-step CRUD sequences.

Sources: [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html) · [stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) · [settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#settings) · [hypothesis-crosshair](https://pypi.org/project/hypothesis-crosshair/) · [CrossHair](https://crosshair.readthedocs.io/) · [Schemathesis](https://schemathesis.readthedocs.io/) · [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html) · [Quint](https://quint.sh/).
