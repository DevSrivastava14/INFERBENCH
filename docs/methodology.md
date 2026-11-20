# InferBench benchmark methodology

This note is the controlled procedure for one benchmark run. It comes from the experiment procedure in the project plan. No number in this file is a measured InferBench result. Day 3 does not rank results and does not call a live model for a recorded timing.

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

Day 3 performs steps 4 through 7 only, and only as a sequential non-streaming run.

The runner checks that the named model is available, then issues warm-up calls, then issues the measured calls. A missing model stops the run before any generate call. Each call waits for the previous call to finish. There is no concurrency argument. Concurrent execution belongs to Day 4.

Steps 1, 2, 8, and 11 wait for Day 7. This day names them and does not collect them. Steps 10 and 12 wait as well. This day does not calculate aggregates, and it does not compare a run with a baseline.

## Warm-up

Warm-up exists because the first inference may include model loading and initialization.

The starting policy is 2–3 warm-up requests, then 3–5 measured repetitions. These are starting values, not permanent rules. They can change after runtime and memory are known.

Warm-up rows are stored. They are excluded from the measured set. Any later aggregate uses the measured set only.

## Prototype defaults

The first runner uses these defaults:

- 2 warm-up calls
- 3 measured calls
- one prompt
- one sequential call at a time

The caller may pass another warm-up count or repetition count inside the starting ranges. The run still uses one prompt and still places one call after another.

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
| outcome | Success, or the adapter error type for that single attempt |
| `eval_count` | Server-reported output token count |
| `prompt_eval_count` | Server-reported prompt token count |
| `prompt_eval_duration` | Server-reported prompt evaluation duration, raw nanoseconds |
| `eval_duration` | Server-reported generation duration, raw nanoseconds |

End-to-end duration is the client clock only. `prompt_eval_duration` and `eval_duration` stay raw integers on the row. They are not copied into the end-to-end duration and they are not converted.

An HTTP chunk is not a token. `eval_count` is the provider output-token count. It is not a count of response lines.

A completed call records the provider counts and the two raw server durations from that call's metadata. A failed call records the error type from that attempt. It does not invent token counts or server durations. The attempt is not repeated. A second call would change the duration the row is supposed to record.

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

A finished experiment must also be able to name hardware, the inference engine version, CPU and RAM samples, and the database that stores the run. Day 7 owns those fields. Day 3 does not sample the machine, does not read an engine version, and does not write a database.
