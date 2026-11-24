---
description: Build the course strictly and fix a broken internal link.
---

# Validate a Documentation Build

By the end of this lesson, you can build the course and identify a broken internal link.

## Before you begin

Start in the course repository with uv installed and a committed `uv.lock`. No cloud credentials are required.

## Build the site

Predict what happens if a page links to a file that does not exist. Then build the current content:

```bash
uv sync --locked
uv run --locked zensical build --clean --strict
```

The build should print `No issues found`, exit with status 0, and create `site/index.html`.

## Practice

1. Add a temporary link to a nonexistent Markdown page.
1. Repeat the build and read the reported source location.
1. Fix the link and rebuild.

## Check your understanding

Which path style lets a strict Zensical build catch a moved target page before publishing?

- [ ] A built HTML URL such as `/guides/install/`
- [ ] A relative Markdown source path such as `../guides/install.md`
- [ ] An external homepage URL

??? question "Reveal answer"

    Use the relative Markdown source path (`../guides/install.md`). Strict builds resolve source paths and heading anchors, while built HTML URLs bypass target validation.

## Completion check

Share one fixed broken-link output with your team, or note the verified build command in your project README. Remove the temporary exercise edit; keep any real source improvement.
