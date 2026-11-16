# Reviewer Standards & Provenance Manifest

Last verified: `2026-11-16`.

## Three-Tier Model-Delta Strategy

Reviewer prompts never vendor third-party guidebooks (copyright, bloat, stale context) and never fetch standard docs at runtime (`5`–`20 s` latency, offline breakage, prompt-injection surface):

1. **Compiled inline model-delta (`<= 80` lines)**: self-contained 1-turn checks encoding concrete Google/industry thresholds and Fmind invariants frontier models otherwise skip.
1. **Tracked provenance manifest (this file)**: maps every role to authoritative primary URLs, verified HTTP `200` on refresh (`Last verified: 2026-11-16`) while CI runs `lychee --offline` syntax/local checks.
1. **Live lookup strictly for volatile target claims**: only `fmind-review-factcheck` enables sanitized HTTPS public web lookup for public product, version, spec, or paper claims; the other 16 roles stay 100% air-gapped.

## Canonical Standards by Role

- **`fmind-review-arch`**: [SWE at Google Ch. 1](https://abseil.io/resources/swe-book/html/ch01.html), [Ch. 15](https://abseil.io/resources/swe-book/html/ch15.html), [Ch. 22](https://abseil.io/resources/swe-book/html/ch22.html), [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/), [Google Cloud Architecture Framework](https://docs.cloud.google.com/architecture/framework), [C4 Model](https://c4model.com/), [Choose Boring Technology](https://mcfunley.com/choose-boring-technology).
- **`fmind-review-code`**: [Google Code Review Standard](https://google.github.io/eng-practices/review/reviewer/looking-for.html), [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), [SWE at Google Ch. 9](https://abseil.io/resources/swe-book/html/ch09.html) & [Ch. 11](https://abseil.io/resources/swe-book/html/ch11.html).
- **`fmind-review-interface`**: [Google AIP](https://google.aip.dev/), [Command Line Interface Guidelines](https://clig.dev/), [Google Style Guides](https://google.github.io/styleguide/).
- **`fmind-review-security`**: [Google Cloud Security](https://docs.cloud.google.com/architecture/framework/security), [Google SAIF](https://safety.google/safety/saif/), [OWASP ASVS](https://asvs.owasp.org/), [OWASP Top 10](https://owasp.org/www-project-top-ten/), [OWASP GenAI](https://genai.owasp.org/), [SLSA](https://slsa.dev/).
- **`fmind-review-ops`**: [Google SRE Books](https://sre.google/books/), [Google Cloud Reliability](https://docs.cloud.google.com/architecture/framework/reliability), [Google Cloud Operational Excellence](https://docs.cloud.google.com/architecture/framework/operational-excellence).
- **`fmind-review-perf`**: [Google SRE Books](https://sre.google/books/), [USE Method](https://www.brendangregg.com/usemethod.html).
- **`fmind-review-finops`**: [FinOps Framework](https://www.finops.org/framework/), [Google Cloud Cost Optimization](https://docs.cloud.google.com/architecture/framework/cost-optimization).
- **`fmind-review-data`**: [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices-performance-overview), [Google Cloud Architecture Framework](https://docs.cloud.google.com/architecture/framework).
- **`fmind-review-mlops`**: [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml), [Google ML Test Score](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/).
- **`fmind-review-ai`**: [Google SAIF](https://safety.google/safety/saif/), [Vertex AI Agent Evaluation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview), [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents).
- **`fmind-review-compliance`**: [SPDX Licenses](https://spdx.org/licenses/), [GDPR (EUR-Lex)](https://eur-lex.europa.eu/eli/reg/2016/679/oj), [EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai), [Google SAIF](https://safety.google/safety/saif/).
- **`fmind-review-docs`**: [Diataxis](https://diataxis.fr/), [Google Developer Doc Style](https://developers.google.com/style), [Google Technical Writing](https://developers.google.com/tech-writing), [SWE at Google Ch. 10](https://abseil.io/resources/swe-book/html/ch10.html), [Agent Skills](https://agentskills.io/specification).
- **`fmind-review-factcheck`**: [Google DeepMind SAFE](https://arxiv.org/abs/2403.18802), [Google Helpful Content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content).
- **`fmind-review-human`**: [Google Developer Doc Style](https://developers.google.com/style), [Google Technical Writing](https://developers.google.com/tech-writing), [NN/g How Users Read on the Web](https://www.nngroup.com/articles/how-users-read-on-the-web/).
- **`fmind-review-design`**: [Material Design 3](https://m3.material.io/), [Nielsen 10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/).
- **`fmind-review-web`**: [Google web.dev](https://web.dev/), [Google Search Central](https://developers.google.com/search/docs), [WCAG 2.2](https://www.w3.org/TR/WCAG22/).
- **`fmind-review-pitch`**: [Minto Pyramid Principle](https://barbaraminto.com/), [Working Backwards PR/FAQ](https://workingbackwards.com/resources/working-backwards-pr-faq/), [April Dunford Positioning](https://www.aprildunford.com/books).
