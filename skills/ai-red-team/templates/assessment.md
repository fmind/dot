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

Use confirmed, refuted, or unresolved for suspected findings. Account separately for blocked actions, target errors, evaluator errors, interrupted trials, and cases not run. State denominators for rates and link to the trial plan when estimating uncertainty.

## Finding and retest

For each confirmed finding: revision and code location; actor and required access; input-to-action trace; observed impact; contrary evidence considered; minimal reproduction; correction; regression result; original and variant retests; remaining risk and owner.

## Coverage and decision

Record the exercised application boundaries, omitted surfaces, unavailable evidence, and differences from production. State whether the declared criteria were met, failed, or remain inconclusive. Successful local tests do not imply authorization to change production.
