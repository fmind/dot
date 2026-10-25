# Promotion and Portability

Read when promoting a guide to its own package or publishing one package outside this catalog. [Package rules](package-rules.md) own the ordinary layout.

## Promotion

Move the guide and owned resources into a new package, rename its entrypoint to `SKILL.md`, add root metadata, fix relative links, and update callers and installation declarations. Remove the former guide rather than keeping two copies. Test the resulting package independently before claiming standalone portability.

## Standalone publication

A first-party catalog may link across global/local owners. Before publishing one package independently, bundle necessary resources or replace sibling paths with available skill-name routing. Include the applicable license and copyright notices from the repository and bundled third-party resources; `license: MIT` metadata alone does not contain those notices. Link the bundled notices from the entrypoint, then validate a disposable copy containing only that package.
