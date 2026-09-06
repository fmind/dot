# Validate a Documentation Build

By the end of this lesson, you can build the course and identify a broken internal link.

## Before you begin

Start in the course repository with uv installed and a committed `uv.lock`. No cloud credentials are required.

## Build the site

Predict what happens if a page links to a file that does not exist. Then build the current content:

```bash
uv sync --locked
uv run zensical build --clean --strict
```

The build should finish without warnings and create `site/index.html`.

## Practice

1. Add a temporary link to a nonexistent Markdown page.
1. Repeat the build and read the reported source location.
1. Fix the link and rebuild.

!!! tip "Check your understanding"

    Why should an internal link use its Markdown source path?

## Completion check

Explain the failure, show the corrected link, and confirm the strict build succeeds. Remove the temporary exercise edit; keep the source improvement if it is useful.
