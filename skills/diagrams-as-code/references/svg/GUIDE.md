---
name: svg
description: "Hand-authored SVG illustrations for READMEs and user docs: composition, branding, embedding, and visual checks."
---

# SVG Illustration Standard

User-facing documentation explains ideas with hand-authored SVG illustrations: still diagram as code, readable and diffable, but composed and branded so the picture carries the concept. [Diagrams as code](../../SKILL.md) owns the choice between SVG, Mermaid, D2, or no diagram. [Brain Framework's README](https://github.com/fmind/brain-framework#readme) is the reference: a loop hero, a before/after contrast, a vocabulary mapping.

## Workflow

1. **Pick the concept**: one idea per illustration (a loop, a before/after, a mapping, a boundary, layers) tied to the section it replaces or reinforces. A README earns a hero illustration under its opening plus one per key concept; split instead of shrinking past 3–7 items per group.
1. **Apply the brand**: use the customer's brand when the repository or engagement belongs to one (palette, fonts, logo, voice); otherwise Fmind's `~/.agents/DESIGN.md`. Never mix brands in one asset or invent a customer's palette: ask for its guide when none is in the repository.
1. **Start from the template**: copy [illustration.svg](templates/illustration.svg) to `docs/assets/<concept>.svg` (or the repository's asset folder; in a chezmoi source tree use a dot-prefixed folder such as `.github/assets/` so apply does not deploy it). For a customer brand, swap only the hex values and font names in its `<style>`. Keep its 960px `viewBox`, `role="img"`, `<title>` and `<desc>`, the opaque light card that keeps the art legible on dark themes, and the semantic classes.
1. **Compose on a grid**: the template's three columns (x=32, 320, and 704 with 64px flow gutters) or an even two- or three-column split; 34px chips stepping by 42; numbered steps on flows; uppercase column labels; code font only for commands, paths, and fields. Use the real names from the source, synthetic examples, and no invented metrics or components.
1. **Write the text equivalent**: `<desc>` states the whole mechanism in prose; the Markdown `alt` states the conclusion; the surrounding paragraph still makes the claim without the image.
1. **Embed**: wrap the image in a link to the SVG so narrow screens can open it full size; use relative paths, or absolute raw URLs only when a registry such as PyPI republishes the README.

   ```html
   <a href="docs/assets/concept.svg">
     <img src="docs/assets/concept.svg" alt="Conclusion the reader should take away" width="960">
   </a>
   ```

1. **Check and inspect**: run [check_svg.py](scripts/check_svg.py); it validates well-formedness, a finite `viewBox` with positive dimensions and 960px width, unique IDs, `role="img"`, `aria-labelledby` references to both `<title>` and `<desc>`, the 12px type floor for recognized numeric font sizes, and `<img>`-sandbox hazards, including event-handler attributes (`on*`) and `javascript:` URLs. It screenshots each SVG directly with JavaScript and document network requests blocked, with brand fonts and with Google Sans removed, since most viewers lack it. It finds Chrome or Chromium (`CHROME` overrides); otherwise use [playwright](../../../playwright/SKILL.md) with JavaScript disabled and network requests blocked. Inspect both images for overflow, collisions, contrast, and spelling, which no static check proves.

   ```bash
   python -I ~/.agents/skills/diagrams-as-code/references/svg/scripts/check_svg.py docs/assets/*.svg --render "$(mktemp -d)"
   ```

## Gotchas

- **SVG `<text>` never wraps**: break lines manually and leave about 15% slack inside every box for wider fallback fonts.
- **Assume an `<img>` sandbox**: GitHub and most sites render SVG through `<img>`, which ignores scripts, external fonts, stylesheets, links, and remote images; avoid `<foreignObject>` and embedded raster or base64 fonts.
- **Keep preview controls together**: the renderer uses a fresh `--user-data-dir` with `profile.default_content_setting_values.javascript=2` (block), `--host-resolver-rules=MAP * ^NOTFOUND` (all hosts, including localhost and IP literals), and `--no-proxy-server` (prevent system proxies resolving hosts remotely). `--blink-settings=scriptEnabled=false` also disables Chrome's internal screenshot harness and can produce no PNG. The profile setting preserves that internal harness while blocking SVG scripts. These controls protect document rendering; they are not OS-level network isolation or a general SVG sanitizer.
- **Mask lines behind captions**: use a canvas-colored rectangle rather than routing around the text.
- **Keep type and contrast legible**: keep text at 12px or larger at 960px width and contrast at 4.5:1 on its actual fill; the link to the full-size SVG is the mobile fallback.

## Documentation

- [MDN SVG reference](https://developer.mozilla.org/en-US/docs/Web/SVG) · [Complex images](https://www.w3.org/WAI/tutorials/images/complex/)
- Chromium: [JavaScript content settings](https://chromium.googlesource.com/chromium/src/+/HEAD/components/content_settings/core/browser/content_settings_registry.cc) · [Headless screenshot harness](https://chromium.googlesource.com/chromium/src/+/HEAD/components/headless/command_handler/headless_command.html) · [Host resolver rules](https://chromium.googlesource.com/chromium/src/+/HEAD/net/dns/mapped_host_resolver.h) · [Proxy flags](https://www.chromium.org/developers/design-documents/network-settings/)
- Companion skills: [fmind-visuals](../../../fmind-visuals/SKILL.md) (brand and template), [repository-docs](../../../repository-docs/SKILL.md) (README journey), [mermaid](../mermaid.md) (technical diagrams).
