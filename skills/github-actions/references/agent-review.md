# Review AI Steps in GitHub Actions

Use this pass for any agent harness invoked by Actions. [github-agentic-workflow](../../github-agentic-workflow/SKILL.md) owns GitHub's specific Agentic Workflows product; [secure](../../secure/SKILL.md) owns finding verification.

1. Identify every AI invocation and its real inputs, including prompt files, environment variables, API fetches, artifacts, and build logs. Read called composite actions and reusable workflows at their resolved revisions; report inaccessible or unresolved dependencies as coverage gaps.
1. Establish who can trigger the job and control each input. Follow the event actor, checked-out revision, effective token permissions, available credentials, and tool access through the relevant steps. Do not equate a trusted workflow file with trusted pull-request content.
1. Trace how those inputs reach the agent and how its output reaches shell commands, files, API requests, comments, or publication. Passing data through `env:` can avoid shell interpolation while leaving its contents untrusted to the agent.
1. Verify the enforcement between model decisions and privileged effects. Check that untrusted code is not executed in a credentialed job and that generated commands or artifacts do not bypass the intended validation or review boundary.
1. Reproduce concrete paths with a local fixture or authorized test workflow. Include legitimate automation and attacker-controlled content; compare attempted actions with actual effects. Do not label broad autonomous permissions as a vulnerability without a violated authority boundary.

Report the trigger, actor capability, data path, execution identity, failed control, and consequence together. Separate an input exposure, a possible injection, and a demonstrated unauthorized action. Never submit a test pull request or comment to another repository merely to validate a suspected path.
