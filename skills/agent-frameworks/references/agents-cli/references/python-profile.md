# Generated Python Profile

The generator owns layout and interpreter constraints. Apply [python-stack](../../../../python-stack/references/foundation/GUIDE.md) quality defaults selectively; do not replace the generated app with its library scaffold.

1. **Recheck the Python constraint**: inspect the selected generator version, generated Python range, and lock before carrying that constraint forward.
1. **Keep the generator's choices**: preserve the generated layout, model, and deployment choices. [google-adk](../../google-adk.md) owns `root_agent`, typed tool functions, and SDK behavior.
1. **Close scaffold quality gaps**: replace dummy unit tests with offline behavior tests, remove blanket `[tool.ty.rules]` suppressions, and fix each diagnostic at its source. Keep the generated lint/install commands; wire local tasks to those commands through [mise](../../../../mise/SKILL.md).
1. **Inspect prerelease dependencies and import warnings**: check the generated `google-adk` pin and the lock for alpha or beta packages (the observability resource detector has shipped as an alpha), and recheck import and deprecation warnings on the selected release. Expect `GOOGLE_GENAI_USE_ENTERPRISE=true` rather than the deprecated `GOOGLE_GENAI_USE_VERTEXAI`.
