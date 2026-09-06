# Specify a Product Bet

Default to a reviewable draft. A requested specification may be written as a local draft; implementation and consequential external changes follow the user's authorized scope. Do not invent analytics, customer research, legal requirements, or operational evidence; keep requirements technology-agnostic where possible.

1. **Restate intent**: target user, current problem, desired outcome, business reason, and the evidence supporting the change.
1. **Set the boundary**: goals, non-goals, affected users, systems, data, platforms, and compatibility requirements.
1. **Prioritize journeys**: the primary journey as P1 and later journeys as P2/P3; each delivers value and is testable independently.
1. **Specify behavior**: functional requirements with stable identifiers and observable outcomes, covering permissions, validation, errors, loading, empty states, retries, cancellation, and recovery.
1. **Specify qualities**: measurable security, privacy, accessibility, performance, reliability, operability, portability, and cost constraints that matter here.
1. **Model information**: entities, ownership, lifecycle, retention, classification, and external boundaries without choosing storage.
1. **Define acceptance**: Given/When/Then scenarios with unhappy paths and boundary conditions; tie every must-have requirement to one scenario.
1. **Define learning and rollout**: success and guardrail metrics, instrumentation, rollout stages, rollback conditions, support implications, and the decision the evidence informs.
1. **Review for executability**: remove contradictions, vague adjectives, hidden scope, and unverifiable requirements; surface blocking questions instead of guessing.

Write the specification contract from [briefs](references/briefs.md). For a compact, low-risk change, combine or omit immaterial sections. Always retain the decision summary, goals and non-goals, identified requirements, acceptance and edge cases, relevant data and trust boundaries, and assumptions or open decisions; never omit a section because it exposes unresolved risk. After approval, hand off to implementation-plan, or to [project-backlog](../project-backlog/SKILL.md) only when the user asks for issue drafts.
