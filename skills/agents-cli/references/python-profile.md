# Generated Python Profile

The generator owns layout and interpreter constraints. Apply [python-stack](../../python-stack/SKILL.md) quality defaults selectively; do not replace the generated app with its library scaffold.

1. Inspect the selected generator version, generated Python range, and lock. The previously qualified 1.5.0 scaffold required Python `>=3.11,<3.14` and used Python 3.13; recheck the selected release before carrying that constraint forward.
1. Preserve the generated layout, model, and deployment choices. [google-adk](../../google-adk/SKILL.md) owns `root_agent`, typed tool functions, and SDK behavior.
1. Replace dummy unit tests with offline behavior tests, remove blanket `[tool.ty.rules]` suppressions, and fix each diagnostic at its source. Keep the generated lint/install commands; wire local tasks to those commands through [mise](../../mise/SKILL.md).
1. Inspect prerelease dependencies and import warnings. The earlier ADK 2.8.0 qualification reported an internal `BaseAgentConfig` deprecation warning and alpha GCP telemetry extras; these are dated qualification gaps to recheck, not evidence about the currently selected release.
1. Keep generated provider integration tests separate from offline tests. Provider calls require authorized access and cost; a successful local gate does not establish model quality or deployment readiness.
