# Stored experiments

This index names the five stored series. It names each findings file, the script, the SQLite file, and the factor that run varied. It does not restate a latency. It does not call a configuration better, faster, or an improvement. It does not name a winner. A document is not a latency.

## Workload sensitivity

Script `scripts/run_workload_sensitivity.py`. SQLite `experiments/results/workload-sensitivity.sqlite`. Findings `docs/workload-findings.md`. Four profiles on `gemma3:1b`. Warm-up 2, measured calls 3, concurrency 1. A longer `num_predict` is a cap, not proof the model emitted that many tokens. The file does not recommend a profile.

## Model comparison

Script `scripts/run_model_comparison.py`. SQLite `experiments/results/model-comparison.sqlite`. Findings `docs/model-findings.md`. The same four profiles on `qwen3.5:2b` with `think` false, then on `gemma3:1b` with `think` omitted. This is a cross-model comparison. Experiment G was not run. Thinking on versus off was not run. The file does not recommend a model.

## Serving configuration

Script `scripts/run_serving_config.py`. SQLite `experiments/results/serving-config.sqlite`. Findings `docs/serving-findings.md`. `short_prompt_short_output`. Concurrency 1, then 2, then 4, with `num_thread` omitted. Then concurrency 1 with `num_thread` 4, then the hardware probe's logical CPU count. Gemma omits `think`. Qwen sends `think` false. Concurrency 8 and `num_ctx` were not varied. One factor at a time. The file does not recommend a setting. A CPU sample is not a latency.

## Analysis

Script `scripts/compare_stored.py`. It reads the three SQLite files above and writes `docs/analysis-findings.md`. A delta is candidate minus baseline on stored aggregates. The phase label is the larger of summed client TTFT and summed client decode duration. The file does not name a winner.

## Routing

Script `scripts/run_routing_experiment.py`. SQLite `experiments/results/routing-effectiveness.sqlite`. Findings `docs/routing-findings.md`. `short_prompt_short_output` under static, workload-aware, latency-constrained, and availability-aware, against a `gemma3:1b` static baseline. The retry count stored for that run is 0. The file does not recommend a policy.
