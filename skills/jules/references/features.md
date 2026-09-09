# Jules Feature Map

Use this map when choosing or configuring a capability beyond the quick links in [the skill](../SKILL.md). Read only the pages relevant to the task; the links own commands, schemas, availability, and limitations.

## Discover and Refresh

The [official documentation index](https://jules.google/docs/) was audited on 2026-09-09. Start there and check the changelog linked from the skill when a feature is missing or has changed; follow current upstream navigation if a page moves. Match the installed version, product surface, account, and platform before applying a recipe. This map covers capability families, not every setting or a promise that every feature is enabled locally.

## Capabilities

| Need | What to resolve | Official sources |
| --- | --- | --- |
| Setup and repository access | Check authentication, connected repositories, and AGENTS.md. | [Getting started](https://jules.google/docs/) · [FAQ](https://jules.google/docs/faq/) |
| Remote environment | Prepare dependencies, setup scripts, and environment behavior. | [Environment setup](https://jules.google/docs/environment/) |
| Task lifecycle | Submit a bounded task, review the plan, and manage task state. | [Running tasks](https://jules.google/docs/running-tasks/) · [Planning](https://jules.google/docs/review-plan/) · [Tasks and repositories](https://jules.google/docs/tasks-repos/) · [Repository view](https://jules.google/docs/repo/) |
| Review and delivery | Review changes and verify the resulting repository state. | [Code review](https://jules.google/docs/code/) |
| Proactive and scheduled work | Distinguish scheduled jobs, suggestions, and continuous workflows. | [Scheduled tasks](https://jules.google/docs/scheduled-tasks/) · [Suggested tasks](https://jules.google/docs/suggested-tasks/) · [Continuous AI](https://jules.google/docs/guides/continuous-ai-overview) |
| CLI and API automation | Read task, session, and output contracts for the selected interface. | [CLI reference](https://jules.google/docs/cli/reference/) · [API quickstart](https://jules.google/docs/api/reference/) · [Authentication](https://jules.google/docs/api/reference/authentication) · [Sources](https://jules.google/docs/api/reference/sources) · [Sessions](https://jules.google/docs/api/reference/sessions) · [Activities](https://jules.google/docs/api/reference/activities) |
| Integrations | Discover the currently supported developer-tool connections. | [Integrations index](https://jules.google/docs/integrations/) · [Render](https://jules.google/docs/integrations/render) |
| Usage and troubleshooting | Check current limits and diagnose task or environment failures. | [Usage and limits](https://jules.google/docs/usage-limits/) · [Errors](https://jules.google/docs/errors/) · [Feedback and support](https://jules.google/docs/feedback/) · [FAQ](https://jules.google/docs/faq/) |

## Boundaries

The documented unit is a hosted repository task. Local skills, hooks, MCP configuration, and terminal settings are not automatically inherited. The linked docs and prompt collection do not establish native Agent Skills installation, a local sandbox, or local subagent controls; verify a newly requested capability through current official documentation.
