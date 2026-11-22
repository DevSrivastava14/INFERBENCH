# InferBench module boundaries

This note names who owns each job. It comes from the planned architecture. Day 1 does not build these modules, and it does not add a FastAPI or React scaffold.

The dashboard reads stored measurements. It does not calculate them.

```text
React dashboard
      |
  FastAPI API
      |
Core services: Workload, Metrics, Routing, Optimization
      |
Inference adapters: Ollama, and later llama.cpp if it is added
      |
Local models, CPU and RAM monitoring, SQLite
```

## Responsibilities

**Inference.** Talks to an inference provider through an adapter. Owns model discovery, availability checks, streaming and non-streaming requests, provider metadata, and error normalization. Owns the HTTP stream, including the client timestamp of the first generated content.

**Workload.** Builds and runs the benchmark load. Owns prompts, output-token limits, concurrency, warm-up, repetitions, scheduling, cancellation, and execution status.

**Metrics.** Calculates client-observed TTFT, TPOT, end-to-end latency, generation throughput, request throughput, P50, P95, P99, and error rate from stored request records. Owns percentile calculation.

**Optimization.** Compares stored experiment results, names bottlenecks those results support, and writes recommendations only from measured numbers.

**Routing.** Chooses a model from availability, workload, measured performance, and the selected policy. Policies to support later are static, workload-aware, latency-constrained, and availability-aware fallback.

**Database.** Stores the snapshot, including the profile name, the think flag, the `num_thread` value the caller passed, and the model metadata the caller copied, the request rows, the resource samples, and the aggregate summary the caller already computed. It stores that name, that flag, that thread value or leaves it unset, and those metadata fields, and it does not recompute the summary. It stores request `success` and `error_type`. It does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. It does not call `summarize` and it does not call Ollama. Load returns the stored values and does not recompute them. Unset aggregate fields stay null on load. An omitted `num_thread` loads back as null.

**Monitoring.** Owns CPU and RAM samples and hardware identity. CPU percent is system-wide. System RAM is the whole machine. Process RAM is the resident set of the benchmark process. It does not time tokens and it does not compute a latency.

## Boundaries

These rules keep later days from mixing clocks and owners.

- The metrics module does not call Ollama and does not call `psutil`.
- Adapters do not compute percentiles.
- The optimization module does not invent numbers. A recommendation needs a stored measurement.
- The benchmark runner must not block the FastAPI event loop. That is a later requirement. Day 1 does not build the runner.

A streaming response shows the split. The inference adapter reads the HTTP stream. The stream result carries `first_content_at`, the stamp of the first non-empty `response`. The adapter does not name that stamp TTFT, and it does not compute TPOT, throughput, or a percentile. The adapter sends `think` as a top-level generate field when the caller sets it. When the caller omits it, the key is absent. The adapter does not choose the flag from the model name. The adapter sends `num_thread` in `options` beside `num_predict` when the caller sets it. When the caller omits `num_thread`, that key is absent. An omitted value is not the integer 0.

`app/metrics/latency.py` computes TTFT, decode duration, and TPOT for one stored row. It does not call Ollama.

`app/metrics/statistics.py` computes average, median, P50, P95, P99, and error rate from one stored run. `app/metrics/throughput.py` computes generation throughput and request throughput from that same run. `app/metrics/` still does not call Ollama and does not call `psutil`.

`app/benchmark/` stores the request rows, including the stamp, and it stores `profile_name`, the `think` flag, and the `num_thread` value the caller passes on the run. It still owns warm-up one call at a time, a measured concurrency cap, cancellation of in-flight measured calls, and one request row per started call. It still does not own percentile math, still does not import metrics, and still does not open SQLite. It may call an injected sampler. It still does not set the five execution states. The runner does not choose the think flag from the model name, and it does not choose `num_thread` from the model name or from the logical CPU count. It does not fill quantization, parameter size, model size, or architecture. The metrics module does not open an HTTP connection.

`app/benchmark/workload.py` is the profile catalog. The runner stores `profile_name`. The snapshot stores the thread value the caller passed, or leaves it unset. It also stores the think flag and the model metadata the caller copied. The live script is a caller outside the runner, and that script is what opens the database. Do not add `app/optimization/`. `app/metrics/` still does not call Ollama and does not call `psutil`.

`app/monitoring/` owns CPU and RAM samples and hardware identity. It does not time tokens.

`app/database/` stores the snapshot, including `profile_name`, the think flag, the `num_thread` value the caller passed, and the model metadata the caller copied, the rows, the samples, and the summary. It stores that name, that flag, that thread value or leaves it unset, and those metadata fields, and it does not recompute the summary. It does not call `summarize` and it does not call Ollama. Load returns the stored aggregate fields, including nulls, and does not recompute them. `app/metrics/` still does not call Ollama and does not call `psutil`.

## Execution states

Later benchmark runs must use these states. They are requirements only. Nothing sets them today.

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

## Who owns the two easy-to-mix jobs

| Job | Owner |
|---|---|
| Percentile calculation | Metrics |
| HTTP stream | Inference adapter |
