# AI Security Assessment

## Scope and identity

| Field                                                    | Value |
| -------------------------------------------------------- | ----- |
| Application and revision                                 |       |
| Model, retrieval snapshot, tool versions                 |       |
| Actor and existing authority                             |       |
| Permitted targets, data, actions, and providers          |       |
| Protected assets and forbidden outcomes                  |       |
| PyRIT, scenario, converter, and scorer versions          |       |
| Cases, repeats, turns, retries, and concurrency          |       |
| Time, token, and cost limits; stop and cleanup procedure |       |
| Evidence location, access, and retention                 |       |

## Cases and results

| Case | Attacker input surface | Preconditions | Legitimate control case | Outcome assertion | Attempted action | Completed effect | Verdict and evidence |
| ---- | ---------------------- | ------------- | ----------------------- | ----------------- | ---------------- | ---------------- | -------------------- |
|      |                        |               |                         |                   |                  |                  |                      |

Label findings `confirmed`, `refuted`, or `unresolved`, separating blocked actions, target/evaluator errors, interrupted trials, and skipped cases (with rate denominators and trial-plan links).

## Finding and retest

Per confirmed finding: revision and `path:line`, actor/access, input-to-action trace, impact, contrary evidence, minimal reproducer, fix, regression + variant retests, residual risk, and owner.

## Coverage and decision

List exercised boundaries, omitted surfaces, missing evidence, production diffs, and verdict (`met`, `failed`, or `inconclusive`; local passes do not authorize production changes).
