# Trail of Bits Incorporation Review

Reviewed on 2026-09-11 against [trailofbits/skills at 321ccfe628eca0d314b0ee4eaffcdd8a05639aaf](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf). This records catalog fit and the provenance of the approaches considered; it is not an installation approval for the upstream marketplace.

## Scope and disposition

Screened all 42 marketplace entries. Examined the nine selections below through their entrypoints or commands, package metadata, selected supporting references, and relevant hook, workflow, and network surfaces. Inventoried 238 files across those packages, with no symlinks. Supporting scripts and upstream evaluation suites were not executed or exhaustively audited.

The upstream repository uses [CC-BY-SA-4.0](https://github.com/trailofbits/skills/blob/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/LICENSE). No upstream prose, code, assets, or templates are vendored here. Local procedures are independently authored for this repository's existing review contracts, with immutable links to the evaluated sources. Importing or adapting upstream expression later requires preserving its applicable license and attribution; do not relabel it MIT.

| Upstream selection | Decision | Local behavior |
| --- | --- | --- |
| [audit-context-building](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/audit-context-building) | Incorporate into `secure` | Read relevant callers and identify who enforces each security assumption; scale the record to the task. |
| [differential-review](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/differential-review) | Incorporate into `diff-review` | Trace changed controls, callers, history, and regressions. No severity formula based on file counts. |
| [fp-check](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/fp-check) | Incorporate into `secure` | Require a falsifiable claim, control-path evidence, contrary evidence, and a confirmed/refuted/unresolved verdict. |
| [insecure-defaults](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/insecure-defaults) | Incorporate into `secure` | Exercise effective configuration and missing/error cases. Honor deliberate authority choices; assess reachable failures. |
| [sharp-edges](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/sharp-edges) | Extend existing `threat-model` and `secure` coverage | Examine security API contracts and ambiguous sentinel values; distinguish granted autonomy from attacker escalation. |
| [variant-analysis](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/variant-analysis) | Incorporate into `secure` | Search related instances of a demonstrated root cause using `rg`, `ast-grep`, and caller analysis. |
| [property-based-testing](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/property-based-testing) | Extend `test-driven-development` | Distinguish a broken guarantee from an invalid generated input or incorrect property; test authority invariants alongside legitimate actions. |
| [supply-chain-risk-auditor](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/supply-chain-risk-auditor) | Extend `secure`; retain native auditors | Keep advisory identity, publisher evidence, install behavior, and unavailable evidence separate. |
| [agentic-actions-auditor](https://github.com/trailofbits/skills/tree/321ccfe628eca0d314b0ee4eaffcdd8a05639aaf/plugins/agentic-actions-auditor) | Incorporate into `github-actions` | Trace untrusted content through AI steps to privileged effects, including indirect file and API inputs. |

## Integration differences

- Upstream context-building, defaults, and variant packages include workflow dispatch or agent orchestration. This catalog keeps procedures usable across harnesses and does not import that runtime.
- `fp-check` includes prompt-based `Stop` and `SubagentStop` hooks that can reject completion. Those hooks are not imported; verification remains part of the requested review.
- The supply-chain collector reads registry/advisory metadata and obtains a GitHub token through `gh auth token` for GitHub API requests. It is not run or imported; existing lockfile and installed-environment audits retain their ownership.
- No new Semgrep, CodeQL, or OpenGrep dependency is introduced. Pattern searches identify candidates; code tracing and tests establish impact.
- No tool permission, sandbox, release-age, provenance, or workstation migration setting is changed by these incorporation decisions.

## Defer the remaining selections

The other 33 entries do not justify new global owners for this task. Language-specific auditing, smart contracts, cryptography, firmware, Android, YARA, and formal proofs need a concrete engagement before adoption. Burp parsing needs a Burp workflow. Static-analysis and rule-authoring packages do not match the selected tool scope. Mutation testing and broader fuzzing remain project-driven extensions of testing; existing repository, GitHub, Python, documentation, and agent skills already own the overlapping general workflows. Organizational, Tarot, and unrelated UI utilities are outside this security addition.

Revisit this record when a repeated task lacks an owner or an upstream update offers a materially different capability. Review the new immutable selection and license before importing any executable surface.
