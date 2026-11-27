# Property Tests & Verification Ladder

Escalate verification depth to match blast radius—Python-native properties run directly against deployed types and code without external model drift.

## Verification Ladder

| Tier                           | Tools (Project-Local)                                                                            | Target Scope                                                            |
| :----------------------------- | :----------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- |
| **1. Baseline**                | `ty`, Pydantic, Ruff, `pytest` (branch cov); opt-in: `diff-cover`, `import-linter`, `ast-grep`   | Every repository; fast local/CI gate.                                   |
| **2. Behavioral & Fuzzing**    | `hypothesis` (`@given`, `RuleBasedStateMachine`), `schemathesis`, scoped `mutmut`                | Parsers, codecs, state transitions, ASGI APIs, core domain logic.       |
| **3. Symbolic & Policy Proof** | `hypothesis-crosshair` (Z3 on Python), `z3-solver`                                               | Authz/IAM/RBAC rules, pricing/billing math, narrow security guards.     |
| **4. Formal Design Model**     | **Quint** (modern TLA+, `npm`/`mise`) — see [adr-rfc.md](../../../../docs/references/adr-rfc.md) | Distributed protocols, sagas, consensus, or locking _designs_ pre-code. |

- **Skip Lean 4 for standard Python**: external Lean models drift from CPython implementations; reserve theorem provers for crypto primitives or compiled policy kernels.

## Hypothesis, Symbolic Execution & Fuzzing

Add `hypothesis` (`uv add --group <test-group> hypothesis`) as the primary Tier 2 multiplier on parsers, codecs, normalizers, schedulers, and stateful workflows:

- **Core invariants**: assert round-trips (`decode(encode(x)) == x`), idempotence (`f(f(x)) == f(x)`), metamorphic invariants (reordering preserves outputs), and oracle equivalence against a trivial slow reference.
- **CI profile & state**: `CI` activates Hypothesis's `ci` profile (derandomized, no deadline, prints `@reproduce_failure(...)` — replay locally on the same version, then remove). Promote counterexamples to `@example(...)`, reset mutable state inside each test body (fixtures run once per test, not per example), and use `RuleBasedStateMachine` for multi-step repository/cache/queue invariants.
- **Security & policy equivalence**: generate multi-principal sequences asserting tenant isolation and denial alongside authorized successes (catches deny-all bugs); add `z3-solver` only for exhaustive symbolic IAM, CIDR, or guardrail equivalence proofs.
- **Symbolic execution (`hypothesis-crosshair`)**: on pure parsers, authz, or numeric guards where random sampling misses narrow branches, run `@given` tests via CrossHair's Z3 backend (`settings.register_profile("crosshair", backend="crosshair")` + `pytest --hypothesis-profile=crosshair`); keep opt-in outside fast PR gates.
- **Stateful ASGI fuzzing (`schemathesis` 4.x)**: test Litestar (`"/schema/openapi.json"`) or FastAPI (`"/openapi.json"`) in-process via `schemathesis.openapi.from_asgi(path, app)`: `@schema.parametrize()` + `case.call_and_validate()` for endpoint/500 checks, and `schema.as_state_machine()` (overriding `before_call` for auth) for multi-step CRUD sequences.

Sources: [Hypothesis](https://hypothesis.readthedocs.io/en/latest/quickstart.html) · [stateful](https://hypothesis.readthedocs.io/en/latest/stateful.html) · [hypothesis-crosshair](https://pypi.org/project/hypothesis-crosshair/) · [CrossHair](https://crosshair.readthedocs.io/) · [Schemathesis](https://schemathesis.readthedocs.io/) · [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html) · [Quint](https://quint.sh/).
