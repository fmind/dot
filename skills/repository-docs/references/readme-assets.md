# README Assets

Use when creating or changing a README logo, illustration, or badge; the reader journey and acceptance review live in [README guidance](readme.md).

## Visual identity

- **Default to a project-owned SVG logo** in a stable asset path such as `docs/assets/logo.svg`. Reuse an established mark; new marks should be simple and recognizable at small sizes. Keep editable vector sources, a `viewBox`, and explicit display dimensions; around 96–128 pixels is a starting point for a standalone mark, not a fixed rule for wordmarks.
- **Make the logo portable**: use self-contained SVG paths/shapes with no scripts, remote resources, or required installed fonts. Outline lettering when needed. Include meaningful image alt text and keep the name and purpose as real text outside the image. SVG syntax validation does not replace visual inspection.
- **Check light and dark themes**: prefer one mark that works on both, or use GitHub's supported `picture` pattern with a fallback. Verify at narrow/mobile and desktop widths without tiny text or horizontal scrolling. A large banner must earn its space by explaining the product.
- **Illustrate concepts with SVG**: place a hero illustration of how the project works under the opening, then one illustration per key concept (a loop, a before/after, a mapping, a boundary) where it replaces paragraphs. Follow the [SVG guide](../../diagrams-as-code/references/svg/GUIDE.md): hand-authored, branded, an opaque light card, a full text equivalent, and a link to the full-size file. Keep [Mermaid](../../diagrams-as-code/references/mermaid.md) for contributor, architecture, and reference docs.
- **Respect brand and project identity**: use the customer's brand for a customer project; otherwise follow [fmind-visuals](../../fmind-visuals/SKILL.md) and `~/.agents/DESIGN.md` unless the project specifies another. Retain a distinct project symbol; do not reuse another project's mascot. GitHub controls README text fonts; apply brand typography to owned assets and sites.

Use relative repository assets by default so branches and local previews stay coherent. When package registries or documentation exports require absolute URLs, verify their renderer and asset availability; do not point an unreleased README at an asset that exists only locally.

## Badges with evidence

Use one compact row, usually three or four badges. Each badge answers a decision question, has descriptive alt text, and links to the underlying evidence. Keep styles consistent.

| Badge           | Include when                                               | Link to                                   |
| --------------- | ---------------------------------------------------------- | ----------------------------------------- |
| CI              | The named workflow exists; scope it to the intended branch | That workflow's runs                      |
| Release/package | A release or package actually exists                       | Releases or the package registry          |
| Compatibility   | Supported runtimes/platforms are declared and checked      | Package metadata or support documentation |
| License         | The license has been chosen and is present                 | The actual license file                   |

Coverage, docs builds, downloads, and other badges are optional when they add useful evidence. CI green is not a security certification or proof of production readiness. Omit novelty badges, duplicate signals, unverified claims, and popularity widgets that crowd out the first useful action. Never invent counts or imply adoption from stars.

Private repositories remain private. Prefer local assets and authenticated GitHub links; omit third-party badges that require private metadata or tokens. Do not create public resources merely to make a badge work. Before a first release, use honest development status and the verified source-install route; add release badges after publication.

See [reference patterns](readme.md#reference-patterns) for example READMEs.
