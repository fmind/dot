# Standalone Tailwind for Python Web Applications

Use the upstream standalone `tailwindcss` executable through the project's locked mise toolchain. Preserve an existing asset build; a new Python web project does not need a Node package graph just to compile CSS. [web-frontend](../SKILL.md) owns this workflow; Django or Litestar owns serving and collecting the output.

## Workflow

1. Inspect `tailwindcss --help`, the lock, template locations, static-file serving, and the production build. Use `github:tailwindlabs/tailwindcss` in mise with the platform's official standalone asset; the dot toolchain selects musl Linux assets and native macOS assets.
1. Choose one input and one generated output, such as `assets/styles.css` and `static/css/app.css`. Create the output directory and exclude generated CSS from source formatting. Commit or build it in CI according to the project's existing artifact policy.
1. Register source roots explicitly. For that example layout, adapt:
   ```css
   /* Docs: https://tailwindcss.com/docs/detecting-classes-in-source-files */
   @import "tailwindcss" source(none);
   @source "../templates";
   @source "../src";
   ```
1. Keep complete class names in templates and Python strings. Map a condition to `text-red-600` or `text-green-600`; `text-{{ color }}-600` cannot be discovered. Use `@source inline(...)` only for a bounded set that cannot live in source.
1. Wire compilation into the existing build and development watch, adapting paths rather than creating another asset subsystem:
   ```toml
   # Docs: https://mise.jdx.dev/tasks/
   [tasks."build:css"]
   run = "tailwindcss -i assets/styles.css -o static/css/app.css --minify"

   [tasks."watch:css"]
   run = "tailwindcss -i assets/styles.css -o static/css/app.css --watch"
   ```
1. Make the production build depend on `build:css` before Django `collectstatic` or application packaging. Use `--watch=always` only for an intentional supervisor whose stdin closes; stop task-owned watchers after verification.
1. Verify a clean production build includes a class used only in a nested template, a conditional class, and a class in Python-generated markup. Delete a class from the fixture and rebuild to check source selection. Inspect the rendered page and its CSS response with [playwright](../../playwright/SKILL.md), including keyboard and responsive states.

## Gotchas

- Source paths are relative to the stylesheet; default discovery otherwise starts at the process working directory. Explicit roots make repository-root and CI builds agree.
- Tailwind scans text, not Python or Jinja semantics. Ignored files and dependencies require deliberate source registration.
- Separate source CSS from generated output; watch loops and stale checked-in output can hide an incomplete production build.
- Respect the site's established identity. Resolve design tokens before editing colors; [fmind-visuals](../../fmind-visuals/SKILL.md) owns published Fmind artifacts.

## Documentation

- [Standalone CLI](https://tailwindcss.com/docs/installation/tailwind-cli) · [Source detection](https://tailwindcss.com/docs/detecting-classes-in-source-files)
- Releases: [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
