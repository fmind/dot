---
name: course-development
description: "Build a technical course: lessons, executable labs, prerequisites, guided practice, accessibility, release acceptance. Use when writing or revising a course, chapter, lab, or tutorial."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/course-development
  created: "2026-08-30"
  updated: "2026-09-06"
---

# Develop a Technical Course

Build a course learners can understand, execute, and finish. Use [zensical](../zensical/SKILL.md) as the default course publisher; an existing course repository owns its platform, page schema, and task names. Use [quality-assurance](../quality-assurance/SKILL.md) for a broader test campaign.

## Workflow

1. **Define the learner**: prerequisites, target capability, time, delivery format, and accessibility needs; keep only content that advances the outcome.
1. **Make outcomes observable**: give each lesson a primary capability and a completion signal; introduce terms before using them.
1. **Ground examples**: derive code and counts from shipped source or generated evidence; explain the reason beside a command and distinguish captured output from illustration.
1. **Make practice executable**: state the goal, starting state, a prediction, ordered work, verification, and what remains afterward; label temporary changes and external access/cost.
1. **Review the learner surface**: navigation, reading order, keyboard use, contrast, alt text, mobile layout, copy/paste, and diagrams explained in prose.
1. **Validate progressively**: run the changed lesson's checks and examples, then the repository's learner gate from a clean environment; record unexercised platforms or live services.
1. **Prepare acceptance**: connect outcomes to evidence, known limitations, and a correction path; publication follows the user's authorized scope.

## Optional Reference Profile

Read [reference-course.md](references/reference-course.md) and its [page template](references/page.md) only for a course that adopts those Markdown conventions, seven exercise fields, capture manifest, and task names. Otherwise use the course's own authoring contract.

## Gotchas

- **Prerequisites**: state the required machine or knowledge state, not merely a previous chapter number.
- **Published routes**: preserve URLs or provide tested redirects/aliases when changing them.
- **Exercises**: use meaningful local work by default; live models, cloud resources, and destructive cleanup need their declared authority and limits.
- **Evidence**: a successful site build does not show that a learner can complete the lesson.

## Documentation

- Reference course: `~/mlops-courses/agentops-open-course` (its `AGENTS.md` owns the page frame, gates, and authoring rules).
- Companion skills: [mermaid](../mermaid/SKILL.md) (diagrams), [playwright](../playwright/SKILL.md) (browser checks), [quality-assurance](../quality-assurance/SKILL.md) (test campaign), [production-readiness](../production-readiness/SKILL.md) (proof ladder).
