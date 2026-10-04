---
name: course-development
description: "Design technical courses, lessons, exercises, and executable labs."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/course-development
  created: "2026-08-30"
  updated: "2026-10-04"
---

# Develop a Technical Course

Build a course learners can understand, execute, and finish. Use [documentation-site](../documentation-site/SKILL.md) as the default course publisher; an existing course repository owns its platform, page schema, and task names. Use [quality-assurance](../quality-assurance/SKILL.md) for a broader test campaign.

## Workflow

1. **Define the learner**: prerequisites, target capability, time, delivery format, and accessibility needs; keep only content that advances the outcome.
1. **Make outcomes observable**: give each lesson a primary capability and a completion signal; introduce terms before using them.
1. **Ground examples**: derive code and counts from shipped source or generated evidence; explain the reason beside a command and distinguish captured output from illustration.
1. **Record terminal examples when useful**: follow the [VHS workflow](../fmind-visuals/references/recording.md) for reproducible demos with synthetic inputs; retain the command transcript and a static equivalent for accessibility.
1. **Make practice executable**: state the goal, starting state, a prediction, ordered work, verification, and what remains afterward; label temporary changes and external access/cost.
1. **Review the learner surface**: navigation, reading order, keyboard use, contrast, alt text, mobile layout, copy/paste, and diagrams explained in prose.
1. **Validate progressively**: run the changed lesson's checks and examples, then the repository's learner gate from a clean environment; record unexercised platforms or live services.
1. **Prepare acceptance**: connect outcomes to evidence, known limitations, and a correction path; publication follows the user's authorized scope.

## Optional Reference Profile

Read [reference-course.md](references/reference-course.md) only for a course that adopts the conventions, exercise fields, and task names of the reference course (`~/mlops-courses/agentops-open-course`, whose `AGENTS.md` owns the page frame, gates, and authoring rules). Otherwise use the course's own authoring contract.

## Gotchas

- **Prerequisites**: state the required machine or knowledge state, not merely a previous chapter number.
- **Published routes**: preserve URLs or provide tested redirects/aliases when changing them.
- **Exercises**: use meaningful local work by default; live models, cloud resources, and destructive cleanup need their declared authority and limits.
- **Evidence**: a successful site build does not show that a learner can complete the lesson.

## Documentation

- Companion skills: [mermaid](../diagrams-as-code/references/mermaid.md) (technical diagrams), [svg](../diagrams-as-code/references/svg/GUIDE.md) (concept illustrations), [playwright](../playwright/SKILL.md) (browser checks), [quality-assurance](../quality-assurance/SKILL.md) (test campaign), [production-readiness](../production-readiness/SKILL.md) (proof ladder).
