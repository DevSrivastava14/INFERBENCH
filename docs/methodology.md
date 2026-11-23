# InferBench benchmark methodology

This note is the controlled procedure for one benchmark run. It comes from the experiment procedure in the project plan. No number in this file is a measured InferBench result. Day 7 samples CPU and RAM while a run is in flight and stores the configuration snapshot, the request rows, those samples, and the aggregate summary the caller already computed. It does not recompute that summary, and it does not call a live model for a recorded timing. Day 8 runs four named workload profiles as four separate runs. The model, the warm-up count, the measured count, and the concurrency cap stay the same across those runs. The profile name is stored on the snapshot with the prompt and `num_predict`. Day 9 runs those four profiles on both local models, eight runs in all. The profile, the warm-up count, the measured count, and the concurrency cap stay the same across those runs. The model and the think flag are what change. Day 10 runs five serving configurations on `gemma3:1b`, then the same five on `qwen3.5:2b`. The profile is `short_prompt_short_output`. The profile, the warm-up count, and the measured count stay the same across those runs. Runs 1–3 are the concurrency sweep and omit `num_thread`. Runs 4–5 are the thread sweep and stay at concurrency 1. Gemma omits `think`. Qwen sends `think` false. Day 11 performs procedure step 12 on two stored experiments. The caller supplies the baseline and the candidate. A delta is the candidate's stored aggregate minus the baseline's stored aggregate. An unset side leaves that delta unset. Day 12 selects a model from a catalog the caller already filled. It does not add a procedure step, and it does not rerun step 12. Static returns the configured model. Workload-aware selection is the lowest stored P95 for the requested profile among candidates that pass the capability and size filters. A miss returns no model. This file still does not record a live timing.

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

Day 5 left the runner performing steps 4 through 7 by streaming. Day 6 left procedure step 10 as pure functions on the stored measured rows. Day 7 performs procedure steps 1, 2, 8, and 11. Step 1 is the hardware and environment snapshot. Step 2 is the inference engine name and version on that snapshot. Step 8 is the sample series taken during the run. Step 11 stores the raw rows, the samples, the snapshot, and the summary the caller already computed. Warm-up stays one call at a time and stays out of the measured set. The prototype default remains one measured call at a time: concurrency 1. The caller may set a higher measured cap. The run stores that setting. The measured cap stays as Day 4 wrote it.

Day 8 runs the four profiles as four runs. The model, the warm-up count, the measured count, and the concurrency cap stay the same across those runs. The profile name is stored with the prompt and `num_predict`. Character length is how the prompt was built. Token length is `prompt_eval_count`. Output length is `eval_count`. A longer `num_predict` is a higher cap. It is not proof the model emitted that many tokens.

Day 9 runs the four profiles on both local models, eight runs in all. The models, in this order, are `qwen3.5:2b` and `gemma3:1b`. Each model runs the four profiles in catalog order. The profile, the warm-up count, the measured count, and the concurrency cap stay the same across those runs. The model and the think flag are what change. `think: false` is sent on Qwen so `eval_count` counts completion tokens. Gemma's request does not send `think`. The stored flag is false or null. Size, quantization, parameter size, and architecture come from the live tags and show payload. A missing architecture field stays unset. Qwen versus Gemma is a cross-model comparison. Experiment G is not run, and no model is downloaded. Thinking on versus off stays out.

Day 10 runs five serving configurations on `gemma3:1b`, then the same five on `qwen3.5:2b`. The profile is `short_prompt_short_output`. Warm-up stays 2. Measured calls stay 3. The profile, the warm-up count, and the measured count stay the same across those runs. Within one model, the model stays the same. Two sweeps change one factor at a time. The concurrency sweep is runs 1–3. Those runs change concurrency to 1, then 2, then 4, and omit `num_thread`. The thread sweep is runs 4–5. Those runs stay at concurrency 1 and set `num_thread` to 4, then to the hardware probe's logical CPU count. Gemma's request does not send `think`. Qwen sends `think` false. Thinking is not turned on. `num_thread` is a stored serving option. An omitted value stays unset. It is not stored as 0. Concurrency 8 and `num_ctx` stay unvaried. Resource samples are not latency.

Day 11 performs procedure step 12 on two stored experiments. The caller supplies the baseline and the candidate. A delta is the candidate's stored aggregate minus the baseline's stored aggregate. An unset side leaves that delta unset. The comparison lists the snapshot fields that differ. It names the phase label of each experiment. It reports the stored sample range. It does not name a winner, and it does not call a configuration an improvement. Step 9 still waits. This day does not repeat an experiment for variance, and it does not call Ollama.

The phase label is the larger of the summed client TTFT and the summed client decode duration on successful measured rows. Warm-up stays out. Failed rows and cancelled rows stay out. A row joins the sums only when TTFT and decode duration are both defined. Equal sums greater than zero are even. No qualifying row, or both sums equal to zero, leaves the label unset. The label does not read `eval_duration`. It is the larger client-clock share. It is not a CPU-bound claim, a memory-bound claim, or a latency. Resource samples stay samples. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later.

Day 12 adds routing selection. It does not add a procedure step, and it does not rerun step 12. The caller supplies the catalog and the policy. Static returns the configured model and keeps that name when a constraint fails. Workload-aware selection is the lowest stored P95 for the requested profile among candidates that pass the capability and size filters. Latency-constrained adds the caller's budget as a further filter, then uses that same P95 rank. No eligible model is a decision with no model. The text does not name a winner. Step 9 still waits. This day does not call Ollama. Availability-aware fallback, timeouts, and retries stay on Day 13.

The runner checks the model first, with `show_model`, then issues warm-up stream calls, then issues the measured stream calls. Sampling starts only after `show_model` succeeds. The series covers warm-up and the measured phase. A missing model raises before any sample and before any generate call. Warm-up calls do not overlap. The measured phase limits how many stream calls are in flight to the stored cap.

Cancellation stays as Day 4 wrote it. Cancellation is an explicit signal the caller can set. When it trips during the measured phase, the runner stops launching new measured calls, cancels stream calls already in flight, and returns the run. A cancelled measured attempt is recorded once, with `error_type` `CancelledError`, and is not retried. Calls that have not started are not rows. An Ollama failure still records that adapter error and does not cancel the other measured calls. A cancelled run keeps the samples already taken and stops the loop.

A sampler exception keeps the samples already taken, records the exception type name, and leaves the other measured calls running. The exception does not cancel those calls.

Day 6 performs procedure step 10 as pure functions on the stored measured rows. Warm-up stays out of every aggregate. The functions read the measured rows the runner already stored. They do not run the model again. The database stores that summary and does not call `summarize`.

Step 9 still waits. Day 11 compares two stored experiments. The caller supplies both experiments. A delta is the candidate's stored aggregate minus the baseline's stored aggregate. An unset side leaves that delta unset. This day does not repeat one experiment for variance, and it does not call Ollama. The comparison does not name a winner, and it does not call a configuration an improvement.

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

## Workload profiles

Day 9 runs the four profiles on both local models, eight runs in all. The models, in this order, are `qwen3.5:2b` and `gemma3:1b`. Each model runs the four profiles in catalog order. Warm-up stays 2. Measured calls stay 3. Concurrency stays 1. Those three settings stay the same across the eight runs. One model is in a run at a time. The short prompt, the filler sentence, and the caps stay the Day 8 catalog. `think: false` is sent on Qwen so `eval_count` counts completion tokens. Gemma's request does not send `think`. The stored flag is false or null. The runner does not choose the flag from the model name. Thinking on versus off stays out.

The four profile names, in this order, are `short_prompt_short_output`, `long_prompt_short_output`, `short_prompt_long_output`, and `long_prompt_long_output`.

The short prompt is `Name one fact about local inference.` The filler sentence is `This sentence only makes the prompt longer. ` The long prompt is the short prompt, one space, then that filler sentence 30 times. Both short-prompt profiles share the short string. Both long-prompt profiles share the long string.

Short output sets `num_predict` to 32. Long output sets `num_predict` to 128. A longer `num_predict` is a higher cap. It is not proof the model emitted that many tokens.

Character length is how the prompt was built. Token length is `prompt_eval_count`. Output length is `eval_count`. After a live call, `prompt_eval_count` is the prompt length and `eval_count` is the output length. The cap is not a token count. `eval_count` can be lower than `num_predict`.

The profile name is stored on the snapshot with the prompt and `num_predict`. A missing profile name stays unset. The runner stores the name the caller passes. It does not look up the catalog. Prompt and `num_predict` still come from the caller.

## Serving configuration

Day 10 runs five serving configurations on `gemma3:1b`, then the same five on `qwen3.5:2b`. The profile is `short_prompt_short_output`. Warm-up stays 2. Measured calls stay 3. The profile, the warm-up count, and the measured count stay the same across those runs. Within one model, the model stays the same. Two sweeps change one factor at a time.

The concurrency sweep is runs 1–3. Those runs change concurrency to 1, then 2, then 4, and omit `num_thread`. `num_thread` is omitted on the concurrency sweep.

The thread sweep is runs 4–5. Those runs stay at concurrency 1 and set `num_thread` to 4, then to the hardware probe's logical CPU count.

Gemma's request does not send `think`. Qwen sends `think` false. Thinking is not turned on. `num_thread` is a stored serving option. An omitted value stays unset. It is not stored as 0. Concurrency 8 and `num_ctx` stay unvaried. One run does not change concurrency and `num_thread` together. Resource samples are not latency. The findings file may describe the stored summaries. It may not recommend a thread count or a concurrency cap, or call one configuration an improvement.

## Baseline comparison

Day 11 performs procedure step 12 on two stored experiments. The caller supplies the baseline and the candidate. There is no built-in anchor and no default model. A delta is the candidate's stored aggregate minus the baseline's stored aggregate. An unset side leaves that delta unset. The sign is arithmetic. The comparison reads the stored aggregate. It does not call `summarize`. A stored average that disagrees with the rows stays the stored average. The result has no winner, no improved flag, and no recommendation.

Setting differences are the snapshot fields whose values differ. The fields are model, profile name, prompt, `num_predict`, warm-up count, measured count, concurrency, `think`, `num_thread`, quantization, parameter size, model size, architecture, engine name, engine version, CPU model, logical CPU count, total RAM, and Python version. Matching fields stay off the list. `think` null versus false is a difference. `num_thread` null versus 4 is a difference. An omitted `num_thread` is not the integer 0.

The phase label is the larger of the summed client TTFT and the summed client decode duration on successful measured rows. Warm-up, failed, and cancelled rows stay out, including a failed row that still carries a first-content stamp. A row joins the sums only when TTFT and decode duration are both defined. The larger sum is `prefill` or `decode`. Equal sums greater than zero are `even`. No qualifying row, or both sums equal to zero, leaves the label unset. The label does not use `eval_duration`. It is the larger client-clock share. It is not a CPU-bound claim, a memory-bound claim, or a latency.

Resource min and max for system CPU percent and system RAM used are reported beside the comparison. An empty sample list leaves them unset. A sample of 0 stays in the min. Those numbers are not latency deltas.

When the request-throughput delta and the P95 delta are both defined and both non-zero, the comparison records both signs in one sentence. The sentence uses "higher" or "lower" for each sign. It does not say the candidate is better, worse, or an improvement.

A Qwen-versus-Gemma pair is a cross-model comparison. It is not a quantization result. Step 9 still waits. This day does not repeat an experiment for variance, and it does not call Ollama. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later.

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

## Resource samples

Sampling is optional. With no sampler, the run records no samples. With a sampler, sampling starts only after `show_model` succeeds. The series covers warm-up and the measured phase. Warm-up stays one call at a time and stays out of the measured set. A missing model raises before any sample. A cancelled run keeps the samples already taken and stops the loop. A sampler exception keeps the samples already taken, records the exception type name, and leaves the other measured calls running.

Each sample stores the runner clock, system CPU percent, system RAM used bytes, system RAM total bytes, and the resident set of the benchmark process.

CPU percent is system-wide at the sample instant. System RAM is used bytes and total bytes. Process RAM is the resident set of the benchmark process, in bytes. System RAM is the whole machine, which includes Ollama. Process RAM is this process. This day does not search for the Ollama PID.

Samples are not TTFT, not TPOT, not end-to-end latency, and not a throughput. The first non-blocking CPU read can be 0 because the probe has no earlier baseline. That 0 is a sample value. It is not a latency result.

## Configuration snapshot

The snapshot stores profile name, model, prompt, `num_predict`, warm-up count, measured count, concurrency, `num_thread`, engine name, engine version, capture time, CPU model, logical CPU count, total RAM bytes, and Python version. The profile name is stored with the prompt and `num_predict`. A missing profile name stays unset. The snapshot also stores the think flag and the model metadata the caller copied: quantization, parameter size, model size in bytes, and architecture. Those four metadata fields come from the live tags and show payload. A missing architecture field stays unset. `think: false` is sent on Qwen. Gemma's request does not send `think`. The stored flag is false or null. The snapshot stores the `num_thread` value the caller passed, or leaves it unset. An omitted value stays unset. It is not stored as 0. The runner does not choose the flag from the model name, and it does not choose `num_thread` from the model name or from the logical CPU count. It does not fill quantization, parameter size, model size, or architecture. The live script copies those fields onto the snapshot. Hardware comes from an injectable probe. Engine name and engine version are strings the caller passes. Engine version is the string the caller stored. The runner does not fetch it.

Concurrency remains a reproducibility field. The run stores the measured concurrency setting. `num_thread` is a stored serving option on that same snapshot.

## Persistence

The database stores the snapshot, every request row, warm-up included, the resource samples, and the aggregate summary the caller already computed. Load returns those stored values and does not recompute them. It stores request `success` and `error_type`. It does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. It does not call `summarize`. Unset aggregate fields stay null on load. It does not call Ollama and it does not sample the machine.

## Routing selection

Day 12 adds routing selection. It does not add a procedure step, and it does not rerun step 12. The caller supplies the catalog and the policy. The router does not call Ollama, does not call `psutil`, and does not call `summarize`. It does not open SQLite. It does not recompute a percentile. Step 9 still waits. This day does not call Ollama. Availability-aware fallback, timeouts, and retries stay on Day 13.

The policy names are `static`, `workload_aware`, and `latency_constrained`. An unknown policy name raises `ValueError`.

A catalog entry holds the model name, capability strings, `model_size_bytes` or unset, and a mapping from profile name to a measurement. A measurement holds `average_ms`, `median_ms`, `p50_ms`, `p95_ms`, and `p99_ms`, each present or unset. The caller copies those numbers from a stored aggregate. The router does not recompute them. Catalog order is the tie break. The router does not prefer a model by name.

A request holds the profile name, the required capability strings, `max_model_size_bytes` or unset, a latency budget or unset, and the static model name or unset. The profile name is a string. An unknown profile matches no measurement. The router does not import the workload catalog.

Required capabilities are an exact, case-sensitive subset of the candidate's set. An empty requirement filters nothing. A set size cap passes when `model_size_bytes` is present and `model_size_bytes` is less than or equal to the cap. Equal size passes. A missing size fails a set cap. No cap means size is not a filter. An omitted size is not the integer 0.

Static returns the configured model name. A missing configured name raises `ValueError`. The decision still returns that name when the model fails a capability check, a size check, or a P95 check, and it lists those failures. Failure labels, in this order, are `capability`, `model_size`, and `p95_missing`. A latency budget on the request is ignored, so `latency_budget` is not a static failure. The decision still returns the configured name when that name is absent from the catalog, with `in_catalog` false, `stored_p95_ms` unset, and an empty failure list. Static does not switch to another model.

Workload-aware selection is the lowest stored P95 for the requested profile among candidates that pass the capability and size filters. Equal P95 keeps the earlier catalog entry. A missing P95 is not selected. A miss returns no model. The decision has no selected model and an empty failure list. A latency budget on the request is ignored.

Latency-constrained adds the caller's budget as a further filter, then uses that same P95 rank. The budget is one of the five latency field names and a maximum. The stored value must be present and less than or equal to the maximum. Among models that pass, the lowest stored P95 for that profile is selected. A missing budget, or a metric name outside those five fields, raises `ValueError`. No eligible model returns no selection.

The decision holds `policy`, `selected_model` or unset, `in_catalog`, `stored_p95_ms` or unset, `failed_constraints`, and `reason`. `in_catalog` is true when the selected model is in the catalog. It is false when static names a model that is absent, and when workload-aware or latency-constrained selects nobody. `stored_p95_ms` is the P95 the rank used, or the static model's stored P95 when that value is present. The decision type has no field named winner, improved, recommendation, or best. The reason does not contain better, worse, improved, winner, recommend, or best. The text does not name a winner.

Capability words are labels the caller supplies. The router does not invent a capability from a model name.

## What this day still does not do

Step 9 still waits. This day does not add a procedure step, and it does not rerun step 12. This day does not call Ollama. Availability-aware fallback, timeouts, and retries stay on Day 13. No eligible model is a decision with no model. The text does not name a winner. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later. It does not set the five execution states. It does not start FastAPI.
