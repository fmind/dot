---
name: monitoring
description: "Monitor ML data quality, drift, labeled performance, lineage, and bounded model explanations."
---

# Monitor Model Quality

This guide owns data and predictive-behavior changes against a versioned reference window; [observability](../../observability/SKILL.md) owns service logs, traces, latency, and errors.

- **Never equate drift with degradation**: input drift alone does not prove accuracy loss or concept drift; without labels, report the missing evidence and the proxies' limits.
- **Treat SHAP as descriptive**: explain only on request or for a concrete finding, with the exact model version and a documented background sample; attributions are not causal evidence.
- **Keep telemetry free of raw data**: retain lineage to join predictions and outcomes without copying private rows into telemetry.
- **Never let drift promote a model**: notifications and automated retraining are configured only within scope; replacements still go through [model-delivery](model-delivery.md).
- **Prove the monitor fires**: run a stable and a deliberately shifted fixture and check emitted severity and recovery; verify the real scheduler ([scheduled-jobs](../../scheduled-jobs/SKILL.md)) separately before claiming continuous monitoring.

## Documentation

- [MLflow evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [SHAP](https://shap.readthedocs.io/en/latest/) · [SHAP releases](https://github.com/shap/shap/releases).
