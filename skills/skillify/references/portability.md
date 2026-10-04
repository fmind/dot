# Promotion and Portability

Read when promoting a guide to its own package, publishing one package outside this catalog, or adding host-specific metadata. [Package rules](package-rules.md) own the ordinary layout.

## Promotion

Move the guide and owned resources into a new package, rename its entrypoint to `SKILL.md`, add root metadata, fix relative links, and update callers and installation declarations. Remove the former guide rather than keeping two copies. Test the resulting package independently before claiming standalone portability.

## Standalone publication

A first-party catalog may link across global/local owners. Before publishing one package independently, bundle necessary resources or replace sibling paths with available skill-name routing; validate a disposable copy containing only that package.

## Host metadata

Add `agents/openai.yaml` only for needed interface metadata, dependencies, or an explicit invocation policy. Link it from the entrypoint; use supported fields and preserve existing user-selected invocation behavior. Host-specific selection settings do not establish cross-host discovery behavior.
