# InferBench benchmark methodology

This note is the controlled procedure for one benchmark run. It comes from the experiment procedure in the project plan. No number in this file is a measured InferBench result. Day 6 calculates aggregate metrics from stored measured rows. It does not call a live model for a recorded timing.

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

Day 5 left the runner performing steps 4 through 7 by streaming. Day 6 does not change that runner. Warm-up stays one call at a time and stays out of the measured set. The prototype default remains one measured call at a time: concurrency 1. The caller may set a higher measured cap. The run stores that setting.

The runner checks that the named model is available, then issues warm-up stream calls, then issues the measured stream calls. A missing model stops the run before any generate call. Warm-up calls do not overlap. The measured phase limits how many stream calls are in flight to the stored cap.

Cancellation stays as Day 4 wrote it. Cancellation is an explicit signal the caller can set. When it trips during the measured phase, the runner stops launching new measured calls, cancels stream calls already in flight, and returns the run. A cancelled measured attempt is recorded once, with `error_type` `CancelledError`, and is not retried. Calls that have not started are not rows. An Ollama failure still records that adapter error and does not cancel the other measured calls.

Day 6 performs procedure step 10 as pure functions on the stored measured rows. Warm-up stays out of every aggregate. The functions read the measured rows the runner already stored. They do not run the model again.

Steps 1, 2, 8, 9, 11, and 12 still wait. Hardware, engine version, CPU and RAM samples, and the database stay Day 7 fields. This day names them and does not collect them. This day does not compare a run with a baseline.

## Warm-up

Warm-up exists because the first inference may include model loading and initialization.

The starting policy is 2–3 warm-up requests, then 3–5 measured repetitions. These are starting values, not permanent rules. They can change after runtime and memory are known.

Warm-up is one call at a time. Warm-up rows are stored. They are excluded from the measured set. Every aggregate reads the measured set only.

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
| client start | Benchmark-process time immediately before the stream call |
| first-content stamp | Benchmark-process time of the first non-empty `response` string |
| client end | Benchmark-process time immediately after that call returns or raises |
| end-to-end duration | Client end minus client start, in milliseconds |
| outcome | Success, the adapter error type for that single attempt, or `CancelledError` for a cancelled measured attempt |
| `eval_count` | Server-reported output token count |
| `prompt_eval_count` | Server-reported prompt token count |
| `prompt_eval_duration` | Server-reported prompt evaluation duration, raw nanoseconds |
| `eval_duration` | Server-reported generation duration, raw nanoseconds |

Client start, the first-content stamp, and client end are three reads of the same benchmark-process clock.

The stamp is the first non-empty `response` string. An empty `response` does not start the first-content clock. A blank line and the final done object do not start the stamp and do not replace it. The row stores the stamp.

Request-level TTFT, decode duration, and TPOT use the formulas already on the metric sheet:

- TTFT = time of first generated content − request start, in milliseconds.
- Decode duration = request completion − first generated content, in milliseconds.
- TPOT = decode duration / (output tokens − 1), in milliseconds per token.

The output-token count is `eval_count`. TPOT is undefined below 2 output tokens. That row still keeps TTFT and end-to-end latency when those two are defined.

End-to-end duration is the client clock only. `prompt_eval_duration` and `eval_duration` stay raw integers on the row. They are not copied into the end-to-end duration, they are not decode duration, and they are not converted.

An HTTP chunk is not a token. `eval_count` is the provider output-token count. It is not a count of response lines.

A completed call records the provider counts and the two raw server durations from that call's metadata. A failed call records the error type from that attempt. It does not invent token counts or server durations. The attempt is not repeated. A second call would change the duration the row is supposed to record.

A cancelled measured attempt records `error_type` `CancelledError` once and is not retried. A call that never started is not a row. A failed Ollama call records its adapter error once. That failure does not cancel the other measured calls.

The adapter error types are the ones the Ollama adapter already raises: `OllamaUnavailableError`, `ModelNotInstalledError`, `MalformedResponseError`, and `OllamaTimeoutError`.

## Aggregate metrics

Aggregates read the measured rows only. Warm-up rows stay stored and stay out of every aggregate.

The latency sample is end-to-end duration on measured rows that succeeded. Failed rows and `CancelledError` rows stay out of the average, the median, and the percentiles, even when they carry a duration. An empty successful sample leaves average, median, and all three percentiles unset.

Average is the arithmetic mean of that sample. Median is the middle value when the count is odd, and the mean of the two middle values when the count is even.

P50, P95, and P99 use nearest-rank on that same sample, sorted ascending. Rank is `ceil(percent * n / 100)`, 1-based, clamped to the sample. Each percentile returns that observed latency. Median uses the ordinary middle, so an even count can differ from nearest-rank P50.

Generation throughput sums `eval_count` and sums client decode duration, then divides, in tokens per second. Decode duration is the client-observed interval from the first-content stamp to client end. `eval_duration` is not the denominator. A row joins both sums only when it succeeded, decode duration is present and positive, and `eval_count` is present. One output token still counts. No such row leaves generation throughput unset. Summed decode time can exceed the wall-clock window when calls overlap.

Request throughput divides completed measured requests by the measured window, in requests per second. The window is the latest measured `client_end` minus the earliest measured `client_start`, in seconds. Failed and cancelled rows still set that pair when they are the extremes. Warm-up timestamps stay out of that pair. Completed means the row succeeded. No measured rows, or a window of zero, leaves request throughput unset. Zero completed requests over a positive window is 0.

Error rate is failed measured requests divided by the measured requests that were not cancelled, as a fraction from 0 to 1. Failed means the row did not succeed and `error_type` is not `CancelledError`. A cancelled row is outside the error rate: it is not a failure and it is not a completed request. All cancelled, or no measured rows, leaves the rate unset. Zero failures on a non-empty population is 0.

## What this day still does not do

The runner stays as Day 5 left it. This day does not capture hardware, does not record the engine version, does not sample CPU and RAM, does not repeat experiments, does not store summaries, and does not compare a run with a baseline. Steps 1, 2, 8, 9, 11, and 12 still wait.

## Later reproducibility fields

Concurrency is a reproducibility field. The run stores the measured concurrency setting.

A finished experiment must also be able to name hardware, the inference engine version, CPU and RAM samples, and the database that stores the run. Those stay Day 7 fields. Day 6 names them and does not collect them. This day does not sample the machine, does not read an engine version, and does not write a database.
