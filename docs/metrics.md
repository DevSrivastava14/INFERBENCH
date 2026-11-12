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

Server-reported prompt timing is a different measurement. It stays in its own field.

## Time per output token (TPOT)

| | |
|---|---|
| Formula | Decode duration / (output tokens − 1) |
| Unit | milliseconds per token |
| Clock | Client-observed duration. The token count is not a clock. |

Decode duration is the client-observed time from the first generated content until the request finishes.

The output-token count comes from provider metadata or a compatible tokenizer. It does not come from the number of HTTP chunks. If that count is approximate, the TPOT value must be labeled an estimate.

TPOT is undefined when the output-token count is less than 2, because the denominator would be zero. That request still keeps its TTFT and end-to-end latency.

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

The output-token count comes from provider metadata or a compatible tokenizer. Chunk count is not the numerator.

## Request throughput

| | |
|---|---|
| Formula | Completed requests / measurement duration |
| Unit | requests per second |
| Clock | Client-observed |

Measurement duration is the client-observed length of the measured window, in seconds. Failed requests are not completed requests, so they stay out of the numerator. They still count in the error rate.

## P50, P95, and P99 latency

| | |
|---|---|
| Formula | Percentiles of the client-observed latency sample. P50 is the middle. P95 is the value at which about 95 percent of requests were faster. P99 is the value at which about 99 percent were faster. |
| Unit | milliseconds, the same unit as the latency sample |
| Clock | Client-observed |

The latency sample is end-to-end latency unless a later experiment explicitly names another client-observed latency. An average can hide a slow tail. These three percentiles keep that tail visible.

Day 1 records the definition only. It does not choose a percentile ranking algorithm. That choice belongs to the metrics engine on a later day.

## Error rate

| | |
|---|---|
| Formula | Failed requests / total requests |
| Unit | fraction from 0 to 1 |
| Clock | Not a timing clock. Both counts are client-observed request outcomes. |

Total requests includes failed requests. A run with no requests has no error rate.

## Server-reported fields that stay separate

Ollama may return these fields. InferBench preserves them beside the client clocks and does not substitute them.

| Field | What it is | Clock |
|---|---|---|
| `prompt_eval_count` | Server-reported prompt token count | Not a clock |
| `prompt_eval_duration` | Server-reported prompt evaluation duration | Server-reported |
| `eval_count` | Server-reported output token count | Not a clock |
| `eval_duration` | Server-reported generation duration | Server-reported |

`prompt_eval_duration` is not client-observed TTFT. `eval_duration` is not client-observed end-to-end latency, and it is not automatically the client-observed decode duration. Their raw unit is recorded when Day 2 reads the live API. Day 1 does not assume that unit.

`eval_count` may supply the output-token count used in TPOT and generation throughput. Using that count does not turn those metrics into server-reported clocks. The durations in those formulas remain client-observed.
