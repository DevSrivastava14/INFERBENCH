# InferBench module boundaries

This note names who owns each job. It comes from the planned architecture. Day 1 does not build these modules, and it does not add a FastAPI or React scaffold.

The dashboard reads the API. It does not calculate the measurements.

Day 14 adds `frontend/` as the reader of measurements it is given. The dashboard does not calculate TTFT, TPOT, percentiles, throughput, or error rate. It does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The four pages are Overview, Benchmark configuration, Results, and Experiment history. FastAPI and the five execution states stay out. A chart draws a series it is given. A chart is not a new latency formula. Selection is not a percentile.

Day 15 adds `app/main.py` and `app/api/` as the caller that opens SQLite, calls `summarize`, and starts the runner. FastAPI owns the connection. Job status is the API's column. The five names `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED` are that column. Request rows stay `success` and `error_type`. The runner does not set those five names. The dashboard reads the API. It still does not calculate TTFT, TPOT, percentiles, throughput, or error rate, and it still does not call Ollama, `psutil`, or SQLite. Comparisons and Routing join the shell. `job_status` is nullable. Load leaves it null when the column is absent and does not alter the file.

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

**Optimization.** Compares two stored experiments the caller supplies. A delta is the candidate's stored aggregate minus the baseline's stored aggregate. It names the larger client-clock phase of each experiment. It does not name a winner, and it does not call a configuration an improvement.

**Routing.** Chooses a model from a catalog the caller already filled. `app/routing/policies.py` holds static, workload-aware, latency-constrained, and availability-aware selection. `app/routing/router.py` holds `route`. `may_fallback` is a pure helper in the routing package. It reads measured rows the caller passes. Routing does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The live script is the caller that opens the database and calls `show_model`. It does not name a winner.

**Database.** Stores the snapshot, including the profile name, the think flag, the `num_thread` value the caller passed, and the model metadata the caller copied, the request rows, the resource samples, and the aggregate summary the caller already computed. It stores that name, that flag, that thread value or leaves it unset, and those metadata fields, and it does not recompute the summary. It stores request `success` and `error_type`. It does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. It does not call `summarize` and it does not call Ollama. Load returns the stored values and does not recompute them. Unset aggregate fields stay null on load. An omitted `num_thread` loads back as null. The snapshot also stores `routing_policy`, `preferred_model`, `fallback_count`, and `retry_count`. An omitted value stays unset. A column that is absent from an older stored file loads as null. Load does not alter that file. `job_status` is nullable. Load leaves it null when that column is absent and does not alter the file.

**Monitoring.** Owns CPU and RAM samples and hardware identity. CPU percent is system-wide. System RAM is the whole machine. Process RAM is the resident set of the benchmark process. It does not time tokens and it does not compute a latency.

**API.** `app/main.py` and `app/api/` are the caller. FastAPI opens SQLite, calls `summarize`, and starts the runner. FastAPI owns the connection. Job status is the API's column. Request rows stay `success` and `error_type`. The runner does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`.

**Dashboard.** `frontend/` reads the API. It does not calculate TTFT, TPOT, percentiles, throughput, or error rate. It does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The pages are Overview, Benchmark configuration, Results, Experiment history, Comparisons, and Routing. A chart draws a series it is given. A chart is not a new latency formula. Selection is not a percentile.

## Boundaries

These rules keep later days from mixing clocks and owners.

- The metrics module does not call Ollama and does not call `psutil`.
- Adapters do not compute percentiles.
- The optimization module reads stored experiments. It does not invent numbers. It does not call Ollama, it does not call `psutil`, it does not open SQLite, and it does not call `summarize`. It does not name a winner.
- The routing module selects from a catalog the caller supplies. It does not call Ollama, it does not call `psutil`, it does not open SQLite, and it does not call `summarize`. It does not name a winner. The live script is the caller that opens the database and calls `show_model`.
- `frontend/` reads the API. It does not calculate TTFT, TPOT, percentiles, throughput, or error rate. It does not call Ollama, does not call `psutil`, and does not open SQLite. Comparisons and Routing join the shell. FastAPI owns the connection. `app/main.py` and `app/api/` open SQLite, call `summarize`, and start the runner. The runner does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. A chart is not a new latency formula. Selection is not a percentile.
- The benchmark runner must not block the FastAPI event loop. That is a later requirement. Day 1 does not build the runner.

A streaming response shows the split. The inference adapter reads the HTTP stream. The stream result carries `first_content_at`, the stamp of the first non-empty `response`. The adapter does not name that stamp TTFT, and it does not compute TPOT, throughput, or a percentile. The adapter sends `think` as a top-level generate field when the caller sets it. When the caller omits it, the key is absent. The adapter does not choose the flag from the model name. The adapter sends `num_thread` in `options` beside `num_predict` when the caller sets it. When the caller omits `num_thread`, that key is absent. An omitted value is not the integer 0.

`app/metrics/latency.py` computes TTFT, decode duration, and TPOT for one stored row. It does not call Ollama.

`app/metrics/statistics.py` computes average, median, P50, P95, P99, and error rate from one stored run. `app/metrics/throughput.py` computes generation throughput and request throughput from that same run. `app/metrics/` still does not call Ollama and does not call `psutil`.

`app/benchmark/` stores the request rows, including the stamp, and it stores `profile_name`, the `think` flag, and the `num_thread` value the caller passes on the run. It still owns warm-up one call at a time, a measured concurrency cap, cancellation of in-flight measured calls, and one request row per started call. It still does not own percentile math, still does not import metrics, and still does not open SQLite. It may call an injected sampler. It still does not set the five execution states. The runner does not choose the think flag from the model name, and it does not choose `num_thread` from the model name or from the logical CPU count. It does not fill quantization, parameter size, model size, or architecture. The metrics module does not open an HTTP connection.

`app/benchmark/workload.py` is the profile catalog. The runner stores `profile_name`. The snapshot stores the thread value the caller passed, or leaves it unset. It also stores the think flag and the model metadata the caller copied. The live script is a caller outside the runner, and that script is what opens the database. `app/benchmark/` still does not own percentile math, still does not import metrics, and still does not open SQLite. `app/metrics/` still does not call Ollama and does not call `psutil`.

`app/optimization/comparison.py` compares two stored experiments with `compare`. `app/optimization/experiments.py` names the phase label. The optimization module reads stored experiments. It does not call Ollama, it does not call `psutil`, it does not open SQLite, and it does not call `summarize`. The findings script is the caller that opens the database and names the pairs. `app/benchmark/` still does not own percentile math, still does not import metrics, and still does not open SQLite. `app/metrics/` still does not call Ollama and does not call `psutil`. The database still stores the summary it was given and does not recompute it. FastAPI and the five execution states stay out.

`app/routing/policies.py` holds static, workload-aware, latency-constrained, and availability-aware selection. `app/routing/router.py` holds `route`. Routing does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The live script is the caller that opens the database and calls `show_model`. It does not name a winner. FastAPI and the five execution states stay out.

`app/monitoring/` owns CPU and RAM samples and hardware identity. It does not time tokens.

`app/database/` stores the snapshot, including `profile_name`, the think flag, the `num_thread` value the caller passed, `routing_policy`, `preferred_model`, `fallback_count`, `retry_count`, and the model metadata the caller copied, the rows, the samples, and the summary. It stores that name, that flag, that thread value or leaves it unset, those routing fields or leaves an omitted value unset, and those metadata fields, and it does not recompute the summary. It does not call `summarize` and it does not call Ollama. Load returns the stored aggregate fields, including nulls, and does not recompute them. A column that is absent from an older stored file loads as null. Load does not alter that file. `job_status` is nullable. Load leaves it null when that column is absent and does not alter the file. `app/metrics/` still does not call Ollama and does not call `psutil`.

`frontend/` reads the API. It does not calculate TTFT, TPOT, percentiles, throughput, or error rate. It does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The pages are Overview, Benchmark configuration, Results, Experiment history, Comparisons, and Routing. FastAPI owns the connection. The benchmark, metrics, optimization, routing, monitoring, and database calculation boundaries stay as Day 14 wrote them, aside from the nullable `job_status` load. A chart draws a series it is given. A chart is not a new latency formula. Selection is not a percentile.

## Execution states

`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED` are the API job. Job status is the API's column. Request rows stay `success` and `error_type`. The runner does not set these five states.

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
