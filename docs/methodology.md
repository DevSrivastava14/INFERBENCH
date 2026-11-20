# InferBench benchmark methodology

This note is the controlled procedure for one benchmark run. It comes from the experiment procedure in the project plan. No number in this file is a measured InferBench result. Day 4 does not rank results and does not call a live model for a recorded timing.

## Procedure

Every benchmark follows the same order:

1. Capture hardware and environment information.
2. Record the inference engine and version.
3. Record model metadata and configuration.
4. Verify model availability.
5. Perform warm-up requests.
6. Execute the configured workload.
7. Collect request-level measurements.
8. Sample CPU and RAM usage.
9. Repeat experiments.
10. Calculate aggregate metrics and percentiles.
11. Store raw results and summaries.
12. Compare against a baseline.

Day 4 performs steps 4 through 7. Step 6 is a configurable concurrent measured phase. Warm-up stays one call at a time and stays out of the measured set. The prototype default remains one measured call at a time: concurrency 1. The caller may set a higher measured cap. The run stores that setting.

The runner checks that the named model is available, then issues warm-up calls, then issues the measured calls. A missing model stops the run before any generate call. Warm-up calls do not overlap. The measured phase limits how many generate calls are in flight to the stored cap.

Cancellation is an explicit signal the caller can set. When it trips during the measured phase, the runner stops launching new measured calls, cancels generate calls already in flight, and returns the run. A cancelled measured attempt is recorded once, with `error_type` `CancelledError`, and is not retried. Calls that have not started are not rows. An Ollama failure still records that adapter error and does not cancel the other measured calls.

Steps 1, 2, 8, and 11 wait for Day 7. This day names them and does not collect them. Steps 10 and 12 wait as well. This day does not calculate aggregates, and it does not compare a run with a baseline.

## Warm-up

Warm-up exists because the first inference may include model loading and initialization.

The starting policy is 2–3 warm-up requests, then 3–5 measured repetitions. These are starting values, not permanent rules. They can change after runtime and memory are known.

Warm-up is one call at a time. Warm-up rows are stored. They are excluded from the measured set. Any later aggregate uses the measured set only.

## Prototype defaults

The runner uses these defaults:

- 2 warm-up calls
- 3 measured calls
- one prompt
- measured concurrency 1

The caller may pass another warm-up count or repetition count inside the starting ranges, and may set a higher measured cap. Warm-up stays one call at a time either way. The run stores the concurrency value that was requested.

## Request row

Each request, warm-up or measured, is one row.

| Field | What it stores |
|---|---|
| phase | `warmup` or `measured` |
| model | Model name sent to the adapter |
| prompt | Prompt sent to the adapter |
| `num_predict` | Output-token cap sent with the call |
| client start | Benchmark-process time immediately before the generate await |
| client end | Benchmark-process time immediately after that await returns or raises |
| end-to-end duration | Client end minus client start, in milliseconds |
| outcome | Success, the adapter error type for that single attempt, or `CancelledError` for a cancelled measured attempt |
| `eval_count` | Server-reported output token count |
| `prompt_eval_count` | Server-reported prompt token count |
| `prompt_eval_duration` | Server-reported prompt evaluation duration, raw nanoseconds |
| `eval_duration` | Server-reported generation duration, raw nanoseconds |

End-to-end duration is the client clock only. `prompt_eval_duration` and `eval_duration` stay raw integers on the row. They are not copied into the end-to-end duration and they are not converted.

An HTTP chunk is not a token. `eval_count` is the provider output-token count. It is not a count of response lines.

A completed call records the provider counts and the two raw server durations from that call's metadata. A failed call records the error type from that attempt. It does not invent token counts or server durations. The attempt is not repeated. A second call would change the duration the row is supposed to record.

A cancelled measured attempt records `error_type` `CancelledError` once and is not retried. A call that never started is not a row. A failed Ollama call records its adapter error once. That failure does not cancel the other measured calls.

The adapter error types are the ones the Ollama adapter already raises: `OllamaUnavailableError`, `ModelNotInstalledError`, `MalformedResponseError`, and `OllamaTimeoutError`.

## What this day does not calculate

This procedure records rows. It does not calculate:

- TTFT
- TPOT
- generation throughput
- request throughput
- error rate
- P50, P95, or P99

TTFT, TPOT, and first-content timestamps belong to Day 5. Percentile ranking and the metrics engine belong to Day 6. The metric sheet already leaves the ranking algorithm for that day. This note does not choose one.

## Later reproducibility fields

Concurrency is a reproducibility field. The run stores the measured concurrency setting.

A finished experiment must also be able to name hardware, the inference engine version, CPU and RAM samples, and the database that stores the run. Those stay Day 7 fields. Day 4 names them and does not collect them. This day does not sample the machine, does not read an engine version, and does not write a database.
