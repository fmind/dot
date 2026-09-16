---
name: monitoring
description: "Monitor ML data quality, drift, labeled performance, lineage, and bounded model explanations."
---

# Monitor Model Quality

Monitor the deployed model against a versioned reference window. [observability](../../observability/SKILL.md) owns service logs, traces, latency, errors, and resource metrics; this guide owns changes in data and predictive behavior.

1. **Define the monitored population**: model version, prediction time, feature availability, reference/current windows, join keys, important slices, and label arrival delay. Retain enough lineage to associate predictions with inputs and eventual outcomes without copying raw private data into telemetry.
1. **Separate signals**: schema violations, null rates, unknown categories, and distribution changes describe inputs; labeled loss or task metrics describe performance. Input drift alone does not prove accuracy degradation or concept drift. Without labels, report the missing evidence and monitor proxies with their limitations.
1. **Use meaningful comparisons**: control for seasonality, sample size, changing cohorts, and delayed labels. Fix metric definitions and windows before comparing results; account for many feature/slice tests when choosing alert thresholds. Do not infer a quality improvement from a changed dataset or an aggregate that hides a failing slice.
1. **Explain when needed**: when an explanation is requested or a concrete finding needs investigation, load the exact model version and use an appropriate method, such as SHAP, on a representative permitted sample with a documented background. Record preprocessing and feature names. Attributions describe model behavior under their assumptions; they are not causal evidence. Preserve negative and uncertain findings.
1. **Make alerts actionable**: define signal, threshold, minimum sample, owner, investigation link, and recovery criterion. Persist reports locally when only an assessment is requested; configure notifications or automated retraining only within scope. A drift report must not directly promote a replacement model.
1. **Verify the monitor**: run a stable reference/current fixture and a deliberately shifted or invalid fixture; check emitted metrics, severity, and recovery. Add delayed-label and empty-window cases when applicable. Verify the actual scheduler and delivery channel separately before claiming continuous monitoring.

## Documentation

- [MLflow evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [MLflow releases](https://github.com/mlflow/mlflow/releases).
- [SHAP documentation](https://shap.readthedocs.io/en/latest/) · [SHAP releases](https://github.com/shap/shap/releases).
- [model-delivery](model-delivery.md) owns evaluation before promotion; [scheduled-jobs](../../scheduled-jobs/SKILL.md) owns workstation scheduling.
