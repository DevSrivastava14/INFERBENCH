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

**Database.** Stores experiment configuration, model metadata, workload settings, request measurements, aggregate metrics, status, errors, and the hardware snapshot. It does not compute live metrics.

**Monitoring.** Samples CPU and RAM during a run, including system memory and process memory where that is possible. It does not time tokens.

## Boundaries

These rules keep later days from mixing clocks and owners.

- The metrics module does not call Ollama.
- Adapters do not compute percentiles.
- The optimization module does not invent numbers. A recommendation needs a stored measurement.
- The benchmark runner must not block the FastAPI event loop. That is a later requirement. Day 1 does not build the runner.

A streaming response shows the split. The inference adapter reads the HTTP stream, records the client timestamp of the first generated content, and stores provider fields such as `eval_count` on the request record. The metrics module then computes TTFT, TPOT, and the percentiles from those records. The adapter does not publish P95. The metrics module does not open an HTTP connection.

`app/benchmark/` owns this recording: warm-up, repetitions, and one request row per sequential call. It still does not own percentile math.

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
