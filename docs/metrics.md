# InferBench metric sheet

This sheet records the formulas InferBench must not get wrong. It comes from the metric definitions in the project plan. No number in this file is a measured InferBench result. Day 1 does not run a benchmark.

Two clocks stay separate.

- **Client-observed** means a timestamp taken by the benchmark process around the HTTP call.
- **Server-reported** means a field returned by the inference server, such as an Ollama duration or token count. Those fields explain work inside the server. They are not copied into client-observed TTFT or end-to-end latency.

HTTP stream chunks are not tokens. A chunk is a piece of the response body. It is not one output token, and it is not a substitute for a token count.

## Time to first token (TTFT)

| | |
|---|---|
| Formula | Time of first generated content − request start time |
| Unit | milliseconds |
| Clock | Client-observed |

TTFT is how long the client waits before the first generated content arrives. It is mostly a prefill story. Empty chunks and response headers are not generated content, so they do not start this clock.

`app/metrics/latency.py` computes TTFT for one stored row.

Server-reported prompt timing is a different measurement. It stays in its own field.

## Time per output token (TPOT)

| | |
|---|---|
| Formula | Decode duration / (output tokens − 1) |
| Unit | milliseconds per token |
| Clock | Client-observed duration. The token count is not a clock. |

Decode duration is the client-observed time from the first generated content until the request finishes. `app/metrics/latency.py` computes decode duration for one stored row.

The output-token count comes from provider metadata or a compatible tokenizer. It does not come from the number of HTTP chunks. If that count is approximate, the TPOT value must be labeled an estimate.

TPOT is undefined when the output-token count is less than 2, because the denominator would be zero. That request still keeps its TTFT and end-to-end latency. `app/metrics/latency.py` computes TPOT for one stored row.

## End-to-end latency

| | |
|---|---|
| Formula | Request completion time − request start time |
| Unit | milliseconds |
| Clock | Client-observed |

This is the full wait the client saw. It includes everything around the model call. It is not pure model computation time, and it is not a server-reported eval duration.

## Generation throughput

| | |
|---|---|
| Formula | Output tokens / decode duration |
| Unit | tokens per second |
| Clock | Client-observed decode duration. The token count is not a clock. |

Decode duration in this formula is the same client-observed interval used for TPOT, converted from milliseconds to seconds so the unit is tokens per second.

The output-token count comes from provider metadata or a compatible tokenizer. Chunk count is not the numerator. `eval_duration` is not the denominator.

`app/metrics/throughput.py` computes generation throughput for one stored run. It sums `eval_count` and sums client decode duration from `decode_duration_ms` in `app/metrics/latency.py`, then divides. A measured row joins both sums only when it succeeded, decode duration is present and positive, and `eval_count` is present. One output token still counts. Warm-up rows stay out. A failed row stays out, including a failed row that still carries a first-content stamp. No qualifying row leaves the aggregate unset. Summed decode time can exceed the wall-clock window when calls overlap.

## Request throughput

| | |
|---|---|
| Formula | Completed requests / measurement duration |
| Unit | requests per second |
| Clock | Client-observed |

Measurement duration is the client-observed length of the measured window, in seconds. That window is the latest measured `client_end` minus the earliest measured `client_start`. Failed and cancelled rows stay out of the numerator. Their timestamps still set the window when they are the extremes. Warm-up timestamps stay out of that pair. Completed means the measured row succeeded. No measured rows, or a window of zero, leaves request throughput unset. Zero completed requests over a positive window is 0.

`app/metrics/throughput.py` computes request throughput for one stored run.

## P50, P95, and P99 latency

| | |
|---|---|
| Formula | Nearest-rank percentiles of the client-observed latency sample. P50, P95, and P99 are the observations at ranks `ceil(50 * n / 100)`, `ceil(95 * n / 100)`, and `ceil(99 * n / 100)`. P50 is that ranked observation. It is not the ordinary middle when that rank differs from the median. |
| Unit | milliseconds, the same unit as the latency sample |
| Clock | Client-observed |

The latency sample is end-to-end latency on measured rows that succeeded, unless a later experiment explicitly names another client-observed latency. Warm-up rows, failed rows, and cancelled rows stay out, even when they carry a duration. An empty successful sample leaves all three percentiles unset. An average can hide a slow tail. These three percentiles keep that tail visible.

Average is the arithmetic mean of that same sample. Median is the middle value when the count is odd, and the mean of the two middle values when the count is even. An empty successful sample leaves average and median unset.

P50, P95, and P99 use nearest-rank. Sort the sample ascending. Rank is `ceil(percent * n / 100)`, 1-based, clamped to `1..n`. The result is an observed latency. Median uses the ordinary middle, so an even count can differ from nearest-rank P50.

`app/metrics/statistics.py` computes average, median, P50, P95, and P99 for one stored run.

## Error rate

| | |
|---|---|
| Formula | Failed requests / total requests |
| Unit | fraction from 0 to 1 |
| Clock | Not a timing clock. Both counts are client-observed request outcomes. |

Total requests includes failed requests. A run with no requests has no error rate.

For one stored run, the population is the measured requests that were not cancelled. Failed means `success` is false and `error_type` is not `CancelledError`. A cancelled row is outside the error rate: it is not a failure and it is not in the denominator. All cancelled, or no measured rows, leaves the rate unset. Zero failures on a non-empty population is 0. Warm-up rows stay out.

`app/metrics/statistics.py` computes error rate for one stored run.

## Server-reported fields that stay separate

Ollama may return these fields. InferBench preserves them beside the client clocks and does not substitute them.

| Field | What it is | Clock |
|---|---|---|
| `prompt_eval_count` | Server-reported prompt token count | Not a clock |
| `prompt_eval_duration` | Server-reported prompt evaluation duration, in nanoseconds | Server-reported |
| `eval_count` | Server-reported output token count | Not a clock |
| `eval_duration` | Server-reported generation duration, in nanoseconds | Server-reported |

`prompt_eval_duration` and `eval_duration` are raw nanoseconds. The Ollama 0.40.16 API description says all durations are returned in nanoseconds, and it names both of these fields in nanoseconds. One live `POST /api/generate` final metadata object returned both fields as integers. That call was a connection check. Its timing is not recorded in this file.

`prompt_eval_duration` is not client-observed TTFT. `eval_duration` is not client-observed end-to-end latency, and it is not automatically the client-observed decode duration. The adapter stores the integers and does not convert them.

`eval_count` may supply the output-token count used in TPOT and generation throughput. Using that count does not turn those metrics into server-reported clocks. The durations in those formulas remain client-observed.

## Prompt length and the output cap

An experiment's prompt length is `prompt_eval_count`. That count is the server-reported prompt token count. Character length is how the prompt was built. It is not `prompt_eval_count`.

`num_predict` is the output-token cap sent with the call. A longer `num_predict` is a higher cap. It is not proof the model emitted that many tokens. Output length is `eval_count`. `eval_count` can be lower than the cap.

The latency, throughput, percentile, and error-rate formulas above stay as Day 6 wrote them.

## Model comparison

A model comparison uses the existing formulas. Quantization is not a latency formula. `think: false` is configuration. It is not a metric.

TTFT and TPOT stay the per-row functions in `app/metrics/latency.py`. They are not new aggregate formulas. The latency, throughput, percentile, and error-rate formulas above stay as Day 6 wrote them.

Size, quantization, parameter size, and architecture are metadata from the live tags and show payload. A missing architecture field stays unset. Qwen versus Gemma is a cross-model comparison. Those metadata fields are not substituted into TTFT, TPOT, throughput, or a percentile.

## Serving comparison

A serving comparison uses the existing formulas. `num_thread` and the concurrency cap are configuration. They are not latency formulas. A CPU sample is not a latency. `think: false` on Qwen is configuration. Gemma omits `think`. Thinking on is not a run in this comparison.

An omitted `num_thread` stays unset. It is not stored as 0. Concurrency 8 and `num_ctx` stay unvaried. The latency, throughput, percentile, and error-rate formulas above stay as Day 6 wrote them.

## Experiment comparison

A comparison delta is the candidate's stored aggregate minus the baseline's stored aggregate. An unset side leaves that delta unset. This delta is not a new latency formula. It reads the stored aggregates. It does not replace the latency, throughput, percentile, or error-rate formulas.

The phase label uses the existing TTFT and decode-duration functions. It does not use `eval_duration`. The label is the larger of those two client-clock sums on successful measured rows. It is not a latency formula.

A CPU sample is not a latency. The stored sample range is not a latency delta.

The latency, throughput, percentile, and error-rate formulas above stay as Day 6 wrote them.

## Routing selection

A latency budget reads a stored aggregate and is not a new latency formula. Selection is not a percentile. The rank reads the stored P95 for the requested profile. The router does not recompute that value. A fallback count is not a latency. The timeout this day records is the existing adapter error.

The latency, throughput, percentile, and error-rate formulas above stay as Day 6 wrote them.

## Resource samples

CPU percent, system RAM, and process RAM are samples taken while a run is in flight. They are not a latency formula and they are not a throughput formula. The latency, throughput, percentile, and error-rate formulas above are unchanged.

| | |
|---|---|
| What is stored | System CPU percent at the sample instant, system RAM used bytes, system RAM total bytes, and the resident set of the benchmark process in bytes |
| Unit | CPU percent is a system-wide percent. RAM figures are bytes. |
| Clock | The runner clock names when the sample was taken. The sample is not a client-observed latency. |

CPU percent is system-wide at the sample instant. System RAM is used bytes and total bytes for the whole machine, which includes Ollama. Process RAM is the resident set of the benchmark process, in bytes. It is not the model's memory. This day does not search for the Ollama PID.

Samples are not TTFT, not TPOT, not end-to-end latency, and not a throughput. The first non-blocking CPU read can be 0 because the probe has no earlier baseline. That 0 is a sample value. It is not a latency result.

`app/monitoring/` records these samples and the hardware identity on the configuration snapshot. `app/metrics/` does not call `psutil`. The database stores the samples. It does not turn them into a percentile or a throughput, and it does not call `summarize`.
