# Generated Python Profile

The generator owns layout and interpreter constraints. Apply [python-stack](../../../../python-stack/references/foundation/GUIDE.md) quality defaults selectively; do not replace the generated app with its library scaffold.

1. Inspect the selected generator version, generated Python range, and lock. The 1.5.0 scaffold was qualified with Python 3.13 under `>=3.11,<3.14`, and 1.8.0 still generates that range; recheck the selected release before carrying that constraint forward.
1. Preserve the generated layout, model, and deployment choices. [google-adk](../../google-adk.md) owns `root_agent`, typed tool functions, and SDK behavior.
1. Replace dummy unit tests with offline behavior tests, remove blanket `[tool.ty.rules]` suppressions, and fix each diagnostic at its source. Keep the generated lint/install commands; wire local tasks to those commands through [mise](../../../../mise/SKILL.md).
1. Inspect prerelease dependencies and import warnings. 1.8.0 scaffolds pin `google-adk>=2.9.2,<3.0.0` and still lock the alpha `opentelemetry-resourcedetector-gcp` 1.12.0a0. The `BaseAgentConfig` deprecation warning came from the earlier ADK 2.8.0 qualification; recheck import warnings on the selected release rather than carrying either observation forward.
1. Keep generated provider integration tests separate from offline tests. Provider calls require authorized access and cost; a successful local gate does not establish model quality or deployment readiness.
