---
name: github-pull-request
description: Create or update a GitHub pull request with a structured What, Why, How, and Test-plan body. Use when opening or updating a PR for the current branch.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-pull-request
  created: "2026-06-23"
  updated: "2026-09-08"
---

# GitHub Pull Request

Create or update a pull request for the intended branch and base, using the repository's template and a description proportional to the change. [feature-branch](../feature-branch/SKILL.md) owns branch creation; [git-add-commit-push](../git-add-commit-push/SKILL.md) owns commit and push repair.

## Workflow

1. **Resolve the target**: inspect `git status --short --branch`, the GitHub repository, and `gh pr view --json number,state,url,baseRefName,headRefName,headRefOid`. Distinguish no open PR from authentication or network failure.
1. **Choose the base**: use the user's explicit base, otherwise the existing PR's base, otherwise `gh repo view --json defaultBranchRef`. A PR needs different head and base branches; never assume every repository uses `main`.
1. **Read the actual change**: fetch the selected base, inspect its three-dot diff to `HEAD`, relevant source/tests, and the commits being proposed. Separate uncommitted work from the branch that GitHub will review.
1. **Draft the title and body**: use a short imperative title. Follow the repository PR template; otherwise use What, Why, How, and Test plan only where they add information. Explain the final behavior, reason, validation, and material limits. Write multiline content to a temporary file for `--body-file`.
1. **Publish the current branch within scope**: when creating or updating the PR is authorized, push any intended commits missing remotely even if an upstream already exists. Preserve unrelated work and follow repository hooks.
1. **Create or update the open PR**: pass the resolved repository and base explicitly; retain the existing base unless changing it was intended. A closed or merged PR is not the open PR for new work.

   ```bash
   gh pr create -R <owner>/<repo> --base <base> --head <head> --title '<title>' --body-file <body-file>
   gh pr edit <number> -R <owner>/<repo> --title '<title>' --body-file <body-file>
   ```

1. **Verify from GitHub**: re-read the PR's title, body, base, head SHA, state, and URL. Compare the head SHA with the intended local commit before reporting the PR URL and validation; local tests do not establish hosted CI.

## Official Skills

Upstream: `cli/cli`, skill `gh`, provides GitHub CLI invocation guidance. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md). Its preview `gh skill` path supports inspection before installation:

```bash
gh skill preview cli/cli gh
```

## Documentation

- [gh pr manual](https://cli.github.com/manual/gh_pr)
- Companion skills: [feature-branch](../feature-branch/SKILL.md), [conventional-commit](../conventional-commit/SKILL.md), [github-issues](../github-issues/SKILL.md).
