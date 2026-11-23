## 2026-11-12 — Day 1: LLM Inference Fundamentals

### Five-line summary

Day 1 is LLM inference fundamentals, and no application code is in scope. `PROGRESS.md` is empty, so nothing from an earlier day needs to be fixed first. The goal is to lock metric formulas, module owners, and the CPU-only model rules before Ollama is connected. `LEARN.md` teaches prefill, decode, tokens, the KV cache, quantization, TTFT, and TPOT with examples marked as illustrations. The day is done when the three docs and the written self-check exist; pytest starts on a later day.

### Completed

- Wrote the metric sheet: formula, unit, and clock label for TTFT, TPOT, end-to-end latency, generation throughput, request throughput, P50/P95/P99, and error rate. HTTP chunks are not tokens. `prompt_eval_duration` and `eval_duration` stay in their own fields.
- Wrote module boundaries. Metrics owns percentiles. The inference adapter owns the HTTP stream. Metrics does not call Ollama. Adapters do not compute percentiles. Optimization does not invent numbers. Execution states are recorded as later requirements only.
- Wrote the CPU-only environment and the comparison rule. Qwen3.5 2B versus Gemma3 1B is a cross-model comparison. A quantization comparison of those two models is forbidden. Model sizes and quantization are planning-time facts for Day 2 to re-check.
- Wrote the Day 1 self-check. No application code, no Ollama client, and no scaffold.

### Files changed

- `docs/metrics.md` (added)
- `docs/architecture.md` (added)
- `docs/environment.md` (added)
- `docs/day1-check.md` (added)

### Test results

No pytest suite exists. Day 1 adds no application code, so there was no automated run. `docs/day1-check.md` answers all six required checks. All six passed.

### Problems

None. Nothing failed, and no fix was attempted.

Notes that are not open problems: `docs/environment.md` does not include the planning-time free-storage figure or Qwen vision/tools support, because `TODAY.md` did not require them. `docs/metrics.md` also states three formula edges that `TODAY.md` did not ask for: TPOT is undefined below 2 output tokens, request throughput counts only completed requests, and a run with no requests has no error rate.

### Next steps

Day 2: connect to Ollama, discover the local models, and verify the planning-time model facts against live metadata. Do not treat those facts as measurements until that check. Do not download models for that check.

## 2026-11-19 — Day 2: Ollama Integration

### Five-line summary

Day 2 is Ollama integration: an async adapter for discovery, one streaming generate, and one non-streaming generate. Nothing from Day 1 failed, so the first work is the live model-fact check and the server duration unit that Day 1 left open. The adapter returns text and raw provider metadata and does not calculate TTFT, TPOT, or percentiles. FastAPI, the benchmark runner, and any reported latency stay out of today. The day is done when mocked pytest passes and the live check file records what Ollama actually returned, including any mismatch.

### Completed

- Confirmed the interpreter is Python 3.13.5. Added an async Ollama adapter with list models, show one model, non-streaming generate, and streaming generate. It returns text and the raw provider metadata. It does not compute TTFT, TPOT, throughput, or percentiles, and it does not retry.
- Read live `GET /api/tags` and `POST /api/show` for `qwen3.5:2b` and `gemma3:1b`. Wrote `docs/model-check.md`. No model was downloaded. No planning-time fact in `docs/environment.md` was contradicted. Qwen `thinking.default` is `true`. Gemma's show payload has no thinking field.
- Confirmed `prompt_eval_duration` and `eval_duration` are nanoseconds from the Ollama 0.40.16 API description and one live final metadata object. Recorded that unit in `docs/metrics.md`. The smoke-call timing is not in the docs.
- Added mocked httpx tests under `tests/unit/`. The suite passes with Ollama stopped.

### Files changed

- `requirements.txt` (added)
- `requirements-dev.txt` (added)
- `app/__init__.py` (added)
- `app/core/__init__.py` (added)
- `app/core/config.py` (added)
- `app/core/exceptions.py` (added)
- `app/inference/__init__.py` (added)
- `app/inference/base.py` (added)
- `app/inference/ollama.py` (added)
- `tests/unit/test_ollama.py` (added)
- `docs/model-check.md` (added)
- `docs/environment.md` (updated)
- `docs/metrics.md` (updated)

### Test results

`python -m pytest`: 9 passed in 0.06s. Ollama was stopped for that run. No test asserts a latency number. `docs/model-check.md` came from a live response.

### Problems

None. Nothing failed, and no fix was attempted.

Notes that are not open problems: the request timeout defaults to 120 seconds because `TODAY.md` did not name a length. Error-path tests call `list_models`, and `OLLAMA_HOST` normalization has no test. The non-streaming test compares the whole metadata dict, which includes fixture durations 10 and 20. The live duration read was one non-streaming `gemma3:1b` call; streaming was mocked. Qwen size `2683396812` bytes is marked verified as 2.683 decimal GB against "about 2.7 GB".

### Next steps

Day 3: benchmark methodology. Build a basic benchmark that can execute and record inference measurements, including warm-up, repeated measurements, timing, percentiles, and token counting. Leave TTFT, TPOT, and percentiles out of the adapter. Do not treat the Day 2 smoke call as a benchmark result.

## 2026-11-21 — Day 3: Benchmark Methodology

### Five-line summary

Day 3 is benchmark methodology: a sequential runner that warms up, repeats, and records one row per request. Nothing from earlier days failed, so there is no fix-first work. Rows store client start, client end, end-to-end duration, and provider token counts, and they leave server durations in their own fields. Percentile ranking, TTFT, TPOT, concurrency, and the database wait for later days. The day is done when mocked pytest passes and warm-up rows stay out of the measured set.

### Completed

- Wrote `docs/methodology.md` from the plan's experiment procedure. The starting policy is 2–3 warm-up requests, then 3–5 measured repetitions. Prototype defaults are 2 warm-up calls, 3 measured calls, one prompt, and one sequential call. Warm-up rows are stored and excluded from the measured set. The note names hardware, engine version, CPU and RAM samples, and the database as Day 7 fields and does not collect them. It does not calculate TTFT, TPOT, generation throughput, request throughput, error rate, or P50, P95, and P99, and it does not choose a percentile ranking algorithm.
- Added a sequential runner in `app/benchmark/`. It checks the model with `show_model`, then calls non-streaming `generate` once per warm-up and once per measured repetition. Each call is timed around the await with the process clock. End-to-end duration is client end minus client start, in milliseconds. `eval_count`, `prompt_eval_count`, `prompt_eval_duration`, and `eval_duration` stay raw provider integers. A missing model raises before any generate call. A failed call records the adapter error type and is not retried. The runner does not rank percentiles. `app/inference/ollama.py` was not changed.
- Pointed `docs/architecture.md` at `app/benchmark/` for this recording, and stated that the package still does not own percentile math.
- Added mocked tests with a fake adapter and a fake clock. No live timing was written into `docs/`, `LEARN.md`, or `PROGRESS.md`.

### Files changed

- `docs/methodology.md` (added)
- `app/benchmark/__init__.py` (added)
- `app/benchmark/records.py` (added)
- `app/benchmark/runner.py` (added)
- `docs/architecture.md` (updated)
- `tests/unit/test_benchmark.py` (added)

### Test results

`python -m pytest`: 16 passed in 0.11s. Seven tests are new, and the existing 9 still pass. The run does not contact Ollama. No test asserts a latency number from a live server.

### Problems

None. Nothing failed, and no fix was attempted.

Notes that are not open problems: no test asserts the recorded `prompt_eval_count`, though the fixture sets it to 5. The failed-call test covers one measured call and zero warm-up calls, so it shows that slot was not retried and does not place a failure between later calls. Plan step 9, "Repeat experiments," is excluded because the methodology limits today to steps 4 through 7; the deferred-step list names 1, 2, 8, 10, 11, and 12 and does not repeat step 9.

### Next steps

Day 4: configurable concurrent workload execution. Keep percentile ranking, TTFT, TPOT, and the database on their later days. Do not treat a Day 3 fake-clock duration as a benchmark result.

## 2026-11-21 — Day 4: Async Python and Concurrency

### Five-line summary

Day 4 is configurable concurrent workload execution: warm-up stays one call at a time, and the measured phase takes a concurrency cap that defaults to 1. Nothing from earlier days failed, so there is no fix-first work. A cancelled run stops new calls, cancels calls already in flight, and records each of those attempts once without a retry. Percentile ranking, TTFT, TPOT, throughput, and the database stay on later days. The day is done when mocked pytest passes and the measured phase never exceeds the cap.

### Completed

- Updated `docs/methodology.md` so procedure step 6 is a configurable concurrent measured phase. Warm-up stays one call at a time and stays out of the measured set. The prototype default remains concurrency 1. The caller may set a higher measured cap, and the run stores that setting. A cancelled measured attempt is recorded once with `error_type` `CancelledError`, with no retry and no row for a call that never started. An Ollama failure still records that adapter error and does not cancel the other measured calls. The note does not calculate TTFT, TPOT, generation throughput, request throughput, error rate, or P50, P95, and P99, and it does not choose a percentile ranking algorithm. Hardware, engine version, CPU and RAM samples, and the database stay Day 7 fields and are not collected.
- Taught the existing runner in `app/benchmark/runner.py` to cap in-flight measured `generate` calls with an `asyncio.Semaphore`. Warm-up still loops one call at a time. `show_model` still runs first, and a missing model still raises before any `generate` call. Concurrency defaults to 1. `BenchmarkRun` stores the requested concurrency. A caller-set `asyncio.Event` stops new measured launches, cancels in-flight `generate` calls, records each started attempt once, and returns the run. A failed Ollama call is still one adapter-error row, and the other measured calls keep running. End-to-end duration stays client end minus client start. `eval_count` and `eval_duration` stay raw provider values. `app/inference/ollama.py` was not changed. No `workload.py` or `scheduler.py` was added, and the runner does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`.
- Pointed `docs/architecture.md` at `app/benchmark/` for concurrency and cancellation. The package still does not own percentile math, and it still does not set the five execution states.
- Added mocked tests in `tests/unit/test_benchmark.py` with the fake adapter. No live timing was written into `docs/`, `LEARN.md`, or `PROGRESS.md`.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `app/benchmark/records.py` (updated)
- `app/benchmark/runner.py` (updated)
- `tests/unit/test_benchmark.py` (updated)

### Test results

`python -m pytest`: 19 passed in 0.12s. Three tests are new, and the existing 16 still pass. The run does not contact Ollama. No test asserts a latency number from a live server.

### Problems

None. Nothing failed, and no fix was attempted.

Notes that are not open problems: `app/benchmark/__init__.py` still says the package is sequential recording. TODAY did not list that file. The cancel test checks `CancelledError`, empty token fields, and the calls that never started. It does not check client start, client end, or end-to-end duration on those rows. The cap test snapshots the first pair while they are blocked. The second pair runs after the gate opens, and `max_measured` is checked again after all four finish. Day 2 and Day 3 notes were left as notes.

### Next steps

Day 5: streaming and request-level latency. First-content timing, TTFT, and TPOT stay on that day. Percentile ranking, throughput, and the database stay on their later days. Do not treat a Day 4 fake-clock duration, or a timing from these mocked tests, as a benchmark result.

## 2026-11-21 — Day 5: Streaming and Latency Measurement

### Five-line summary

Day 5 is streaming and request-level latency: the benchmark path reads a stream and stamps the first non-empty content on the runner's clock. Nothing from earlier days failed, so there is no fix-first work. Completion stays client end minus client start, and TTFT, decode duration, and TPOT come from the stored row using the Day 1 formulas. TPOT stays undefined below two output tokens. Percentile ranking, throughput, and the database stay on later days, and the day is done when mocked pytest passes on fixture clocks.

### Completed

- Updated `docs/methodology.md` so procedure steps 4 through 7 run by streaming. Warm-up stays one call at a time and stays out of the measured set. The prototype default remains concurrency 1. The caller may set a higher measured cap, and the run stores that setting. Cancellation stays as Day 4 wrote it. The first-content stamp is the first non-empty `response` string. An empty `response` does not start that clock. A blank line and the final done object do not start the stamp and do not replace it. The row stores the stamp. Request-level TTFT, decode duration, and TPOT use the Day 1 formulas. The output-token count is `eval_count`. TPOT is undefined below 2 output tokens, and that row still keeps TTFT and end-to-end latency when those two are defined. The note does not calculate generation throughput, request throughput, error rate, or P50, P95, and P99, and it does not choose a percentile ranking algorithm. Hardware, engine version, CPU and RAM samples, and the database stay Day 7 fields and are not collected.
- Pointed `docs/architecture.md` at `first_content_at` on the stream result, at `app/metrics/` for TTFT, decode duration, and TPOT on one stored row, and at `app/benchmark/` for storing the row, including the stamp. The benchmark package still does not own percentile math, and it still does not set the five execution states.
- Pointed TTFT, decode duration, and TPOT in `docs/metrics.md` at `app/metrics/latency.py`. The formulas are unchanged. Generation throughput, request throughput, error rate, and percentile ranking stay unimplemented. No ranking algorithm is chosen.
- Taught `generate_stream` to accept the runner's clock and to call it on the first non-empty `response` string. An empty `response` does not call it, and a later piece does not replace a stamp already set. `StreamGenerateResult` carries `first_content_at`. That field is not named TTFT. The result does not carry TTFT, TPOT, throughput, or a percentile. Non-streaming `generate` stays on the adapter. The runner does not call it.
- Switched the runner to `generate_stream` for every warm-up call and every measured call, and passed the runner's clock in. `show_model` still runs first. A missing model still raises before any stream call. Each successful row stores `first_content_at` beside client start, client end, and end-to-end duration. End-to-end duration stays client end minus client start. Client start, the stamp, and client end are three reads of that same clock. `eval_count` stays the provider output-token count. `eval_duration` stays a raw integer. `chunk_count` stays off the row. Warm-up stays one call at a time. The measured cap stays an `asyncio.Semaphore` and still defaults to 1. A failed call records that adapter error once, leaves the stamp unset, and does not cancel the other measured calls. A cancel records each started attempt once as `CancelledError`, leaves the stamp unset, does not retry, and adds no row for a call that never started. The runner does not import metric helpers. `app/benchmark/__init__.py` now describes streaming request rows with a measured concurrency cap.
- Added `app/metrics/latency.py`. From one `RequestRecord`, TTFT is (`first_content_at` − client start) × 1000, decode duration is (client end − `first_content_at`) × 1000, and TPOT is decode duration / (`eval_count` − 1). Each function returns no value when its formula is undefined. A missing stamp leaves all three unset. `eval_count` missing or below 2 leaves TPOT unset and still returns TTFT when the stamp is present. A failed row and a cancelled row leave all three unset. `eval_count` is not labeled an estimate. The metrics module does not call Ollama. It does not calculate generation throughput, request throughput, error rate, or a percentile.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/inference/base.py` (updated)
- `app/inference/ollama.py` (updated)
- `app/benchmark/__init__.py` (updated)
- `app/benchmark/records.py` (updated)
- `app/benchmark/runner.py` (updated)
- `app/metrics/__init__.py` (added)
- `app/metrics/latency.py` (added)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_ollama.py` (updated)
- `tests/unit/test_latency.py` (added)

### Test results

`python -m pytest`: 23 passed in 0.11s. Four tests are new, and the existing 19 still pass. The run uses the fake adapter and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. The teaching clocks, start 0 seconds, first content 0.8 seconds, end 3.0 seconds, and `eval_count` 21, return 800 ms, 2200 ms, and 110 ms. Those numbers are a fixture, not a live result.

### Problems

None. Nothing failed, and no fix was attempted.

Notes that are not open problems: no test passes a successful row with no stamp into the metrics functions, and no test uses a missing `eval_count`. The code leaves all three unset when the stamp is missing, and it leaves TPOT unset when `eval_count` is missing. The tested failure row still carries the 0.8 second stamp, and the three results stay unset. The adapter stamps the first non-empty `response` and does not read the `done` flag. The new stream test covers an empty done object, which does not replace the stamp. A done object that itself contains text would set the stamp if it were the first non-empty piece. Response headers have no separate test. The clock is called only for a non-empty `response` string. Day 2, Day 3, and Day 4 notes were left as notes. The cancel test still does not check client start, client end, or end-to-end duration on cancelled rows.

### Next steps

Day 6: percentile ranking, average and median, generation throughput, request throughput, error rate, and aggregate statistics. CPU and RAM sampling and the database stay on Day 7. Do not treat the Day 5 teaching clocks, or a timing from these mocked tests, as a benchmark result.

## 2026-11-21 — Day 6: Statistics and Throughput

### Five-line summary

Day 6 is statistics and throughput: the metrics engine ranks stored measured rows and computes average, median, both throughputs, and error rate. Nothing from earlier days failed, so there is no fix-first work. Percentiles use nearest-rank on successful end-to-end latencies, and warm-up stays out of every aggregate. Generation throughput divides provider output tokens by client decode time, while request throughput divides completed requests by the measured window. CPU, RAM, and the database stay on Day 7, and the day is done when mocked pytest passes on constructed rows.

### Completed

- Updated `docs/methodology.md` so procedure step 10 is pure functions on the stored measured rows. Warm-up stays out of every aggregate. The runner stays as Day 5 left it. The latency sample is successful measured end-to-end duration. Average is the arithmetic mean. Median is the ordinary middle, so an even count can differ from nearest-rank P50. P50, P95, and P99 use nearest-rank: sort ascending, rank `ceil(percent * n / 100)`, 1-based, clamped to the sample, and the result is an observed latency. Generation throughput sums `eval_count` and sums client decode duration. Request throughput divides completed measured requests by the latest measured `client_end` minus the earliest measured `client_start`. A cancelled row is outside the error rate. Steps 1, 2, 8, 9, 11, and 12 still wait. Hardware, engine version, CPU and RAM samples, and the database stay Day 7 fields and are not collected. This day does not compare a run with a baseline.
- Pointed `docs/architecture.md` at `app/metrics/statistics.py` for average, median, P50, P95, P99, and error rate, and at `app/metrics/throughput.py` for generation throughput and request throughput. `app/benchmark/` still stores the rows, still does not own percentile math, still does not import metrics, and still does not set the five execution states.
- Recorded nearest-rank, the even-count median, the rows that join each throughput sum, and the cancellation rule in `docs/metrics.md`. The existing formula tables stay. "Unimplemented" is removed from average, median, the three percentiles, both throughputs, and error rate.
- Added `app/metrics/statistics.py`. `average_ms`, `median_ms`, and `percentile_ms` read successful measured `end_to_end_ms` only. `error_rate` keeps `CancelledError` out of both counts. An empty population returns no value. Zero failures returns 0. `AggregateSummary` holds the five latency fields, `error_rate`, and both throughput fields. `summarize` fills that object from one `BenchmarkRun`. The functions do not take an adapter and do not open a connection.
- Added `app/metrics/throughput.py`. `generation_throughput_tps` calls `decode_duration_ms` and does not use `eval_duration`. A row joins both sums only when it succeeded, decode duration is present and positive, and `eval_count` is present. One output token still counts. A failed row stays out, including one that still carries a first-content stamp. `request_throughput_rps` divides completed measured requests by the measured window. Failed and cancelled timestamps still set that window. Warm-up timestamps stay out. A window that is not positive leaves request throughput unset. Zero completed requests over a positive window returns 0. `app/metrics/__init__.py` names these aggregates and still says the package does not call Ollama. `app/benchmark/runner.py` and `app/inference/ollama.py` were not changed.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/metrics/__init__.py` (updated)
- `app/metrics/statistics.py` (added)
- `app/metrics/throughput.py` (added)
- `tests/unit/test_statistics.py` (added)
- `tests/unit/test_throughput.py` (added)

### Test results

`python -m pytest`: 42 passed in 0.31s. Nineteen tests are new, and the existing 23 still pass. The run uses constructed rows and the existing mocks. It does not contact Ollama. No test asserts a latency number from a live server. The figures 492, 120, 2000, 7.5, and 0.4 are fixtures, not a live result.

### Problems

None left open.

One new test failed on the first suite run. `test_failed_row_with_stamp_stays_out_of_the_latency_sample` expected nearest-rank P50 of 100 and 110 ms to be 105. That 105 is the median. Nearest-rank P50 of those two values is 100. Average and median had already shown the failed row was out of the sample. The fixture was changed to three successes, 100, 110, and 120 ms, beside the failed row, so average, median, and P50 are all 110 only when that row stays out. The second run passed. The final run passed all 42.

Notes that are not open problems: no test shows a `CancelledError` row setting the request-throughput window. No test shows generation throughput unset when no measured row qualifies. No test shows a measured set of only adapter failures leaving the five latency fields unset. The percentile formula cell in `docs/metrics.md` still says "P50 is the middle," and the paragraph under it names nearest-rank. A negative measured window is treated as unset, the same as a window of zero. Day 2, Day 3, Day 4, and Day 5 notes were left as notes.

### Next steps

Day 7: CPU and RAM sampling, process resource tracking, SQLite, and configuration snapshots. Do not treat a Day 6 fixture duration, or a timing from these mocked tests, as a benchmark result.

## 2026-11-22 — Day 7: Resource Monitoring and Persistence

### Five-line summary

Day 7 is resource monitoring and persistence: sample CPU and RAM during a run, and store the snapshot, rows, samples, and summary in SQLite. Nothing from earlier days failed, so there is no fix-first work. Monitoring owns the samples, metrics stays on stored request clocks, and the database stores without recomputing. Process RSS is the benchmark process, system RAM is the machine, and samples are not latency. Repeating experiments, baseline comparison, and the five execution states stay later, and the day is done when mocked pytest passes.

### Completed

- Updated `docs/methodology.md` so Day 7 performs procedure steps 1, 2, 8, and 11. Step 1 is the hardware and environment snapshot. Step 2 is the inference engine name and version on that snapshot. Step 8 is the CPU and RAM sample series. Step 11 stores the raw rows, the samples, the snapshot, and the summary the caller already computed. Sampling starts only after `show_model`. A missing model raises before any sample. A cancelled run keeps samples already taken and stops the loop. A sampler exception keeps earlier samples, records the exception type name, and leaves the other measured calls running. CPU percent is system-wide. System RAM is used and total bytes for the whole machine. Process RAM is this process's resident set. Samples are not latency and not throughput. The snapshot lists the recorded fields. Engine version is the string the caller stored. The runner does not fetch it. The database stores request `success` and `error_type`, does not set the five execution states, does not call `summarize`, and leaves unset aggregates null on load. Steps 9 and 12 still wait. This day does not repeat experiments and does not compare a run with a baseline.
- Pointed `docs/architecture.md` at `app/monitoring/` for CPU and RAM samples and hardware identity, and at `app/database/` for storing the snapshot, the rows, the samples, and the summary. `app/benchmark/` still stores the request rows, still does not own percentile math, still does not import metrics, and still does not open SQLite. It may call an injected sampler. `app/metrics/` still does not call Ollama and does not call `psutil`.
- Added a resource-samples section to `docs/metrics.md`. The latency, throughput, percentile, and error-rate formulas are unchanged. The percentile formula cell still says "P50 is the middle."
- Added `app/monitoring/`. `ResourceSample` stores the runner clock, system CPU percent, system RAM used and total bytes, and this process's RSS. `read_sample()` uses an injectable probe. The real probe calls `psutil.cpu_percent` with no blocking interval. `capture_hardware()` and `build_snapshot()` copy an injectable hardware probe and the caller-supplied engine name and version. Capture time comes from an injectable clock. Neither function calls Ollama or starts a run.
- Added `engine_version()` on the adapter. It calls `GET /api/version` and returns the version string. A missing version string raises `MalformedResponseError`. The runner does not call that method. `generate`, `generate_stream`, `list_models`, and `show_model` stay as they were.
- Sampling is optional on the runner. The default is no sampler, so the existing tests keep their behavior. With a sampler, the loop starts after `show_model`, takes one sample, awaits the injected sleep for the interval, and repeats until the run returns. The default sleep is `asyncio.sleep`. The default interval is 1 second. A set sampler requires an interval greater than 0. A sampler exception stops later samples, keeps earlier samples, sets `sampling_error` to the exception type name, and leaves inference calls running. Cancel still stops the loop and keeps samples already taken. `BenchmarkRun` stores `resource_samples` and `sampling_error`. The runner still does not import metric helpers and still does not open SQLite.
- Added `app/database/`. SQLAlchemy stores the snapshot, every request row, the resource samples, and nullable aggregate columns. `save_experiment` writes those values. `load_experiment` returns the stored snapshot, warm-up rows, measured rows, samples, `sampling_error`, and aggregate fields, including nulls. It does not call `summarize` and does not recompute throughput or percentiles. Request status is `success` and `error_type`. The five execution states are not stored. `requirements.txt` gained `psutil` and `sqlalchemy` as plain requirement lines.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `requirements.txt` (updated)
- `app/monitoring/__init__.py` (added)
- `app/monitoring/sampler.py` (added)
- `app/monitoring/snapshot.py` (added)
- `app/inference/base.py` (updated)
- `app/inference/ollama.py` (updated)
- `app/benchmark/records.py` (updated)
- `app/benchmark/runner.py` (updated)
- `app/database/__init__.py` (added)
- `app/database/models.py` (added)
- `app/database/repository.py` (added)
- `tests/unit/test_monitoring.py` (added)
- `tests/unit/test_database.py` (added)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_ollama.py` (updated)

### Test results

`python -m pytest`: 54 passed in 0.97s. Twelve tests are new, and the existing 42 still pass. The run uses a fake sampler, a fake hardware probe, a fake clock, constructed rows, and the httpx mock transport. It does not contact Ollama. No test asserts a live CPU number, a live RSS, a live engine version, or a latency number from a live server.

### Problems

None left open.

Nothing failed in the suite, and no product fix was attempted.

Notes that are not open problems: no database test stores a non-null `sampling_error` and reads it back. No test sets `sample_interval` to 0 or below. `engine_version()` has no test of its own for a non-JSON body, a connection failure, or a timeout. `psutil_probe()` and `psutil_hardware_probe()` have no test, because a live CPU percent is not a test result. The percentile formula cell in `docs/metrics.md` still says "P50 is the middle." Day 2, Day 3, Day 4, Day 5, and Day 6 notes were left as notes.

### Next steps

Day 8: workload sensitivity. Prompt length, output length, and short and long requests stay on that day. Do not treat a Day 7 fixture duration, or a timing from these mocked tests, as a benchmark result.

## 2026-11-22 — Day 8: Workload Sensitivity

### Five-line summary

Day 8 is workload sensitivity: four named profiles that cross short and long prompts with short and long output caps. Nothing from earlier days failed, so there is no fix-first work. The profile name is stored with the prompt and `num_predict`, and one live `gemma3:1b` run writes findings only from SQLite. Qwen, concurrency sweeps, thinking mode, and baseline comparison stay on later days. The day is done when mocked pytest passes and the findings file matches the stored rows.

### Completed

- Updated `docs/methodology.md` so Day 8 runs four profiles as four separate runs of `gemma3:1b`. Warm-up stays 2. Measured calls stay 3. Concurrency stays 1. Those settings stay the same across the four runs. The profile names, in order, are `short_prompt_short_output`, `long_prompt_short_output`, `short_prompt_long_output`, and `long_prompt_long_output`. The short prompt is `Name one fact about local inference.` The long prompt is that sentence, one space, then `This sentence only makes the prompt longer. ` thirty times. Short output sets `num_predict` to 32. Long output sets `num_predict` to 128. Character length is how the prompt was built. Token length is `prompt_eval_count`. Output length is `eval_count`. A longer `num_predict` is a higher cap. It is not proof the model emitted that many tokens. The profile name is stored on the snapshot with the prompt and `num_predict`. A missing name stays unset. Steps 9 and 12 still wait. The findings file may describe the four stored summaries. It may not recommend a profile, and it may not call one configuration an improvement.
- Pointed `docs/architecture.md` at `app/benchmark/workload.py` for the profile catalog. The runner stores `profile_name`. The database stores that name and does not recompute the summary. `app/benchmark/` still does not own percentile math, still does not import metrics, and still does not open SQLite. The live script is the caller that opens the database. `app/metrics/` still does not call Ollama and does not call `psutil`.
- Recorded in `docs/metrics.md` that an experiment's prompt length is `prompt_eval_count` and that `num_predict` is the cap. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them. The percentile formula cell still says "P50 is the middle."
- Added `app/benchmark/workload.py` with the four frozen profiles in that order. Added optional `profile_name` on `BenchmarkRun`, on `ConfigurationSnapshot`, and on the experiment row. `run()` and `build_snapshot()` take it as a keyword and default it to unset. `save_experiment` writes the snapshot's name. `load_experiment` returns it. A missing name is stored and loaded as null. The runner still takes the prompt and `num_predict` from its existing arguments and does not look up the catalog. It still does not import metrics, still does not open SQLite, and still does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. `app/inference/ollama.py` was not changed. The request timeout stays 120 seconds.
- Added `scripts/run_workload_sensitivity.py`. For each profile, in catalog order, the script calls `show_model` first, reads the engine version, builds the snapshot with `psutil_hardware_probe` and the real clock, and runs with `psutil_probe` through `read_sample` at a 1-second interval. The script calls `summarize`, then `save_experiment`. The runner does not. SQLite is `experiments/results/workload-sensitivity.sqlite`. `docs/workload-findings.md` was written from the four experiments loaded back out. If the model is missing or Ollama is down, the script exits non-zero and does not write findings numbers. No model was downloaded. The findings file states that the timeout was the adapter default of 120 seconds, that the measured count is 3, and that the file does not recommend a profile. On the long-output profiles, the stored `eval_count` is lower than the cap. No stored `error_type` was set. No figure from that file was copied into `LEARN.md`, `PROGRESS.md`, or a pytest assertion.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/benchmark/workload.py` (added)
- `app/benchmark/records.py` (updated)
- `app/benchmark/runner.py` (updated)
- `app/monitoring/snapshot.py` (updated)
- `app/database/models.py` (updated)
- `app/database/repository.py` (updated)
- `tests/unit/test_workload.py` (added)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_database.py` (updated)
- `tests/unit/test_monitoring.py` (updated)
- `scripts/run_workload_sensitivity.py` (added)
- `experiments/results/workload-sensitivity.sqlite` (added)
- `docs/workload-findings.md` (added)

### Test results

`python -m pytest`: 61 passed in 0.76s. Seven tests are new, and the existing 54 still pass. The run uses the fake adapter, the fake clock, constructed rows, and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. The live script is not collected. `docs/workload-findings.md` was loaded back from `experiments/results/workload-sensitivity.sqlite`. Pytest does not read that file for an expected timing.

### Problems

None left open.

The first launch of `python scripts/run_workload_sensitivity.py` failed before any Ollama call. Python put `scripts/` on the module path, so `import app` raised `ModuleNotFoundError`. No findings file was written, and the database was not created. The script now inserts the project root on `sys.path` before those imports. The second launch exited 0.

`TODAY.md` says the mocked `long_prompt_short_output` run sends `num_predict` 128. That conflicts with the short-output cap of 32. The chosen rule is 32 for that profile. The mocked run stores the name and sends 32. The long-output profiles still use 128.

Notes that are not open problems: the mocked profile run uses 1 warm-up call and 1 measured call. `save_experiment` writes the snapshot's `profile_name`, so a name set only on the run would load back as null. The live script sets both. The catalog check looks at the runner module's names after the call. This live series did not include a system CPU sample of 0. The script keeps a 0 if one is taken. If `show_model` fails after the opening check, the script has already removed any earlier findings file and can leave a partial SQLite file. This run finished all four profiles. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from the findings file. Day 2, Day 3, Day 4, Day 5, Day 6, and Day 7 notes were left as notes.

### Next steps

Day 9: model and quantization analysis. Compare the available local models. A quantization comparison still needs compatible variants of one model. Do not treat a Day 8 live duration, a CPU sample, or a timing from these mocked tests, as a benchmark result. Do not copy a figure from `docs/workload-findings.md` into `LEARN.md` or into a pytest assertion.

## 2026-11-22 — Day 9: Model and Quantization Analysis

### Five-line summary

Day 9 is model and quantization analysis: eight runs cross `qwen3.5:2b` and `gemma3:1b` with the four workload profiles. Nothing from earlier days failed, so there is no fix-first work. Qwen requests send `think` false and that flag is stored; Gemma omits it, and thinking on versus off stays later. No same-model quantization pair was on the tags list, so Experiment G was not run, and the findings stay a cross-model comparison. The day is done when mocked pytest passes and the findings file matches the stored rows.

### Completed

- Updated `docs/methodology.md` so Day 9 runs the four profiles on both local models, eight runs in all. The models, in this order, are `qwen3.5:2b` and `gemma3:1b`. Each model runs the four profiles in catalog order. Warm-up stays 2. Measured calls stay 3. Concurrency stays 1. Those three settings stay the same across the eight runs. One model is in a run at a time. `think: false` is sent on Qwen so `eval_count` counts completion tokens. Gemma's request does not send `think`. The stored flag is false or null. The runner does not choose the flag from the model name. Size, quantization, parameter size, and architecture come from the live tags and show payload. A missing architecture field stays unset. Qwen versus Gemma is a cross-model comparison. Experiment G is not run, and no model is downloaded. Steps 9 and 12 still wait. The findings file may describe the stored summaries. It may not attribute a difference to Q8 versus Q4, recommend a model, or call one configuration an improvement. Thinking on versus off stays out.
- Pointed `docs/architecture.md` at the top-level `think` field. The snapshot stores the flag and the model metadata the caller copied. `app/benchmark/` still does not own percentile math, still does not import metrics, and still does not open SQLite. The live script is the caller that opens the database. `app/optimization/` was not added. `app/metrics/` still does not call Ollama and does not call `psutil`.
- Recorded in `docs/metrics.md` that a model comparison uses the existing formulas and that quantization is not a latency formula. `think: false` is configuration. TTFT and TPOT stay per-row functions. They are not new aggregate formulas. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them. The percentile formula cell still says "P50 is the middle."
- Added `think: bool | None = None` on `GenerateOptions`. When it is set, `_generate_body` sets `body["think"]` beside `stream`. When it is omitted, the key is absent. `num_predict` stays under `options`. Non-streaming `generate` shares that helper and still does not compute TTFT, TPOT, or percentiles. `ModelInfo.architecture` uses `details.family` when that value is a string, otherwise `model_info["general.architecture"]` when that value is a string, and otherwise stays unset.
- `run()` takes `think` and stores it on `BenchmarkRun`. It does not choose the flag from the model name. It does not fill quantization, parameter size, model size, or architecture. `ConfigurationSnapshot` and `build_snapshot` take `think`, `quantization`, `parameter_size`, `model_size_bytes`, and `architecture`, each defaulting to unset. `save_experiment` writes them. `load_experiment` returns them. `think` false loads back as false. An omitted think loads back as null. The database still does not call `summarize`, `ttft_ms`, or `tpot_ms`. The runner still does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. The request timeout stays 120 seconds.
- Added `scripts/run_model_comparison.py`. It refuses to run if the adapter timeout is not 120 seconds. Before deleting any file, it calls `show_model` for both local models and reads `list_models`. It ignores `gemma4:31b-cloud` and `deepseek-v4.1-flash:cloud`. No same-architecture quantization pair was in that list. The script does not download a model. It then runs eight experiments: all four profiles on `qwen3.5:2b` with `think=False`, then all four on `gemma3:1b` with `think` omitted. For each one it reads the engine version, builds the snapshot with `psutil_hardware_probe` and the real clock, and runs with `psutil_probe` through `read_sample` at a 1-second interval. Show payloads omit size, so size is copied from the tags `ModelInfo` when show leaves it unset. The script calls `summarize`, then `save_experiment`. The runner does not. SQLite is `experiments/results/model-comparison.sqlite`. `docs/model-findings.md` was written from the eight experiments loaded back out. The file states that the timeout was the adapter default of 120 seconds, that the measured count is 3, that the file is a cross-model comparison, that Experiment G was not run, that thinking on versus off was not run, and that the file does not recommend a model. On the long-output profiles, the stored `eval_count` is lower than the cap. No stored `error_type` was set. No figure from that file was copied into `LEARN.md`, `PROGRESS.md`, or a pytest assertion.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/inference/base.py` (updated)
- `app/inference/ollama.py` (updated)
- `app/benchmark/records.py` (updated)
- `app/benchmark/runner.py` (updated)
- `app/monitoring/snapshot.py` (updated)
- `app/database/models.py` (updated)
- `app/database/repository.py` (updated)
- `tests/unit/test_ollama.py` (updated)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_database.py` (updated)
- `tests/unit/test_model_comparison.py` (added)
- `scripts/run_model_comparison.py` (added)
- `experiments/results/model-comparison.sqlite` (added)
- `docs/model-findings.md` (added)

### Test results

`python -m pytest`: 75 passed in 1.38s. Fourteen tests are new, and the existing 61 still pass. The run uses the fake adapter, the fake clock, constructed rows, and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not collect the live script, and it does not read `docs/model-findings.md` for an expected timing. A fresh load of the eight stored experiments reproduced that file, including per-row TTFT and TPOT from the latency functions.

### Problems

None left open.

Nothing failed in the suite, and no product fix was attempted. The first launch of `python scripts/run_model_comparison.py` exited 0.

Notes that are not open problems: the database round-trip uses the Day 2 Qwen size integer, which also appears in the findings file. The new findings test asserts TTFT and TPOT from constructed clocks, start 1 second, first content 1.5 seconds, end 2 seconds, and `eval_count` 3. Those numbers are a fixture, and the test does not read the findings file. No test calls `run` on `qwen3.5:2b` without `think` and checks that the flag stays unset. The HTTP assertion for top-level `think: false` is on non-streaming `generate`. Streaming uses the same body helper. This live series did not include a system CPU sample of 0. The script keeps a 0 if one is taken. If `show_model` fails after the opening check, the script has already removed any earlier findings file and can leave a partial SQLite file. This run finished all eight profiles. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from the findings file. Day 2, Day 3, Day 4, Day 5, Day 6, Day 7, and Day 8 notes were left as notes.

### Next steps

Day 10: CPU and serving optimization. Threading, concurrency, serving parameters, and resource utilization stay on that day, and only settings the engine supports. Thinking on versus off, a same-model quantization run, and baseline comparison stay later. Do not treat a Day 9 live duration, a CPU sample, or a timing from these mocked tests, as a benchmark result. Do not copy a figure from `docs/model-findings.md` into `LEARN.md` or into a pytest assertion.

## 2026-11-22 — Day 10: CPU and Serving Optimization

### Five-line summary

Day 10 is CPU and serving configuration: five runs on `gemma3:1b`, then the same five on `qwen3.5:2b`, both on `short_prompt_short_output`, vary client concurrency and `num_thread` one factor at a time. Nothing from earlier days failed, so there is no fix-first work. Gemma omits `think`. Qwen sends `think` false, and thinking is not turned on. Concurrency 8, context length, a same-model quantization run, and baseline comparison stay later. The day is done when mocked pytest passes and the findings file matches the stored rows.

### Completed

- Updated `docs/methodology.md` so Day 10 runs five serving configurations on `gemma3:1b`, then the same five on `qwen3.5:2b`. The profile is `short_prompt_short_output`. Warm-up stays 2. Measured calls stay 3. The profile, the warm-up count, and the measured count stay the same across those runs. The concurrency sweep is runs 1–3: concurrency 1, then 2, then 4, and `num_thread` is omitted. The thread sweep is runs 4–5: concurrency stays 1, and `num_thread` is 4, then the hardware probe's logical CPU count. Gemma's request does not send `think`. Qwen sends `think` false. Thinking is not turned on. An omitted `num_thread` stays unset. It is not stored as 0. Concurrency 8 and `num_ctx` stay unvaried. Steps 9 and 12 still wait. The findings file may describe the stored summaries. It may not recommend a thread count or a concurrency cap, or call one configuration an improvement. Resource samples are not latency.
- Pointed `docs/architecture.md` at `options.num_thread` beside `num_predict`. The snapshot stores the thread value the caller passed, or leaves it unset. `app/benchmark/` still does not own percentile math, still does not import metrics, and still does not open SQLite. The live script is the caller that opens the database. `app/optimization/` was not added. `app/metrics/` still does not call Ollama and does not call `psutil`.
- Recorded in `docs/metrics.md` that a serving comparison uses the existing formulas, and that `num_thread` and the concurrency cap are configuration. `think: false` on Qwen is configuration. A CPU sample is not a latency. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them. The percentile formula cell still says "P50 is the middle."
- Added `num_thread: int | None = None` on `GenerateOptions`. When it is set, `_generate_body` puts `num_thread` in the same `options` object as `num_predict`. When it is omitted, that key is absent. `think` stays a top-level field. Non-streaming `generate` shares that helper and still does not compute TTFT, TPOT, or percentiles. `run()` takes `num_thread` and stores it on `BenchmarkRun`. The runner does not choose it from the model name or from the logical CPU count. `ConfigurationSnapshot`, `build_snapshot`, and `ExperimentRow` store it. `save_experiment` writes the snapshot value. `load_experiment` returns it. An omitted value loads back as null. A stored 4 loads back as 4. The database still does not call `summarize`, `ttft_ms`, or `tpot_ms`.
- Added `scripts/run_serving_config.py`. It refuses to run if the adapter timeout is not 120 seconds. Before deleting any file, it calls `show_model` for `gemma3:1b` and `qwen3.5:2b`. If the logical CPU count from `psutil_hardware_probe` is under 12, it exits before any generate and does not write findings. It then runs ten experiments: the five configurations on `gemma3:1b` with `think` omitted, then the same five on `qwen3.5:2b` with `think=False`. The script calls `summarize`, then `save_experiment`. The runner does not. SQLite is `experiments/results/serving-config.sqlite`. `docs/serving-findings.md` was written from the ten experiments loaded back out. The file states that the timeout was the adapter default of 120 seconds, that the measured count is 3, that Gemma's request does not send `think`, that Qwen was run with `think` false, that thinking was not turned on, that concurrency 8 and `num_ctx` were not varied, and that the file does not recommend a setting. No stored `error_type` was set. The logical CPU count was not under 12, so the high thread setting was that probe count. No figure from that file was copied into `LEARN.md`, `PROGRESS.md`, or a pytest assertion.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/inference/base.py` (updated)
- `app/inference/ollama.py` (updated)
- `app/benchmark/records.py` (updated)
- `app/benchmark/runner.py` (updated)
- `app/monitoring/snapshot.py` (updated)
- `app/database/models.py` (updated)
- `app/database/repository.py` (updated)
- `tests/unit/test_ollama.py` (updated)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_database.py` (updated)
- `scripts/run_serving_config.py` (added)
- `experiments/results/serving-config.sqlite` (added)
- `docs/serving-findings.md` (added)

### Test results

`python -m pytest`: 83 passed in 0.71s. Eight tests are new, and the existing 75 still pass. The run uses the fake adapter, the fake clock, constructed rows, and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not collect the live script, and it does not read `docs/serving-findings.md` for an expected timing. A fresh load of the ten stored experiments reproduced that file, including per-row TTFT and TPOT from the latency functions.

### Problems

None left open.

One draft of the live script nested the Qwen loop and left `save_experiment` outside the inner loop. That draft would have stored only the last run of each model. The save was moved inside the loop before the script was launched. The launch exited 0.

Notes that are not open problems: the mocked serving runs use 1 warm-up call and 1 measured call. `save_experiment` writes the snapshot's `num_thread`, so a value set only on the run would load back as null. The live script sets both. The HTTP assertion for `options.num_thread` beside `num_predict` is on non-streaming `generate`. Streaming uses the same body helper. The script's timeout refusal and its stop for a logical CPU count under 12 have no pytest. If `engine_version` fails after the opening `show_model` checks, the script has already removed any earlier findings file and can leave a partial SQLite file. This run finished all ten configurations. The closing paragraph in `docs/methodology.md` states the Qwen `think` false rule twice. `TODAY.md` still says Qwen is not run. The Qwen grid was added because it was requested, with `think` false and without `think` true. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from the findings file. Day 2 through Day 9 notes were left as notes.

### Next steps

Day 11: performance analysis. Baseline comparison, bottleneck identification, and experiment comparison stay on that day. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later. Do not treat a Day 10 live duration, a CPU sample, or a timing from these mocked tests, as a benchmark result. Do not copy a figure from `docs/serving-findings.md` into `LEARN.md` or into a pytest assertion.

## 2026-11-23 — Day 11: Performance Analysis

### Five-line summary

Day 11 is performance analysis: compare two stored experiments and name which client clock, prefill or decode, takes the larger share. Nothing from earlier days failed, so there is no fix-first work. The caller names the baseline and the candidate, and the delta is candidate minus baseline, with no winner. The findings script is that caller for the workload, model, and serving databases already on disk. The day is done when mocked pytest passes and the findings file matches those stored rows.

### Completed

- Updated `docs/methodology.md` so Day 11 performs procedure step 12 on two stored experiments. The caller supplies the baseline and the candidate. A delta is the candidate's stored aggregate minus the baseline's stored aggregate. An unset side leaves that delta unset. The comparison lists the snapshot fields that differ, names the phase label of each experiment, and reports the stored sample range. It does not name a winner, and it does not call a configuration an improvement. The phase label is the larger of the summed client TTFT and the summed client decode duration on successful measured rows. Warm-up, failed, and cancelled rows stay out. Equal sums greater than zero are even. No qualifying row, or both sums equal to zero, leaves the label unset. The label does not use `eval_duration`. Step 9 still waits. This day does not repeat an experiment for variance, and it does not call Ollama. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later.
- Pointed `docs/architecture.md` at `app/optimization/comparison.py` for `compare` and at `app/optimization/experiments.py` for the phase label. Removed the sentence that said not to add `app/optimization/`. The optimization module reads stored experiments. It does not call Ollama, it does not call `psutil`, it does not open SQLite, and it does not call `summarize`. The findings script is the caller that opens the database and names the pairs. `app/benchmark/` still does not own percentile math, still does not import metrics, and still does not open SQLite. `app/metrics/` still does not call Ollama and does not call `psutil`. The database still stores the summary it was given and does not recompute it. Routing, FastAPI, and the five execution states stay out.
- Recorded in `docs/metrics.md` that a comparison delta is candidate minus baseline on the stored aggregates, and that this delta is not a new latency formula. The phase label uses the existing TTFT and decode-duration functions. It does not use `eval_duration`. A CPU sample is not a latency. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them. The percentile formula cell still says "P50 is the middle."
- Added `phase_label` in `app/optimization/experiments.py`. It returns `prefill`, `decode`, `even`, or no value. It reads successful measured rows only. A row joins the sums only when `ttft_ms` and `decode_duration_ms` both return a value. It does not read `eval_duration`. It does not call Ollama, `psutil`, or `summarize`.
- Added `compare` in `app/optimization/comparison.py`. It returns one frozen result with both experiment ids. For the eight stored aggregate fields, the delta is the candidate's stored field minus the baseline's stored field. A missing field on either side leaves that delta unset. It reads the stored `AggregateSummary` and does not call `summarize`. It stores both phase labels, the differing snapshot fields in the required order, and, for each side, the sample count and the min and max of system CPU percent and system RAM used. No samples leave those four numbers unset. A sample of 0 stays in the min. When the request-throughput delta and the P95 delta are both defined and both non-zero, it stores one sentence of the two signs. Otherwise that sentence is absent. The result type has no winner, improved, or recommendation field.
- Added `load_experiments` in `app/database/repository.py`. It returns every stored experiment in ascending id order and uses the same row mapping as `load_experiment`. It does not call `summarize`, `ttft_ms`, or `tpot_ms`. Unset aggregates stay null. A column that is absent from an older stored file loads as null. A stored think value of 0 loads as false. The function does not alter the file.
- Added `scripts/compare_stored.py`. It inserts the project root on `sys.path` before importing `app`. It reads `experiments/results/serving-config.sqlite`, `experiments/results/workload-sensitivity.sqlite`, and `experiments/results/model-comparison.sqlite` with `load_experiments`, checks every required pair, and writes `docs/analysis-findings.md` only after those checks pass. A missing file, a missing match, or a match that is not unique exits non-zero and does not write the findings file. The script does not construct an Ollama adapter, does not call `generate`, `generate_stream`, `show_model`, or `list_models`, and does not call `summarize`. The pair table is in the script. It is not inside `compare`. The four model pairs are marked as cross-model comparisons. `docs/analysis-findings.md` was written from 15 stored pairs. No figure from that file was copied into `LEARN.md`, `PROGRESS.md`, or a pytest assertion.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/optimization/__init__.py` (added)
- `app/optimization/experiments.py` (added)
- `app/optimization/comparison.py` (added)
- `app/database/repository.py` (updated)
- `tests/unit/test_comparison.py` (added)
- `tests/unit/test_database.py` (updated)
- `scripts/compare_stored.py` (added)
- `docs/analysis-findings.md` (added)

### Test results

`python -m pytest`: 96 passed in 1.76s. Thirteen tests are new, and the existing 83 still pass. The run uses constructed experiments, the in-memory database, the fake adapter, the fake clock, and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not collect the findings script, and it does not read `docs/analysis-findings.md` for an expected timing. A fresh load of the three stored databases reproduced that file, including the phase labels and the deltas. The three SQLite hashes were the same before and after the script.

### Problems

None left open.

The first launch of `python scripts/compare_stored.py` failed before writing findings. `load_experiments` selected `experiments.think`, and SQLite reported that the column was missing. A direct read of `serving-config.sqlite` showed that file does have `think`. `workload-sensitivity.sqlite` was stored before that column existed, so its experiments table has no `think`, `num_thread`, quantization, parameter size, model size, or architecture column. `model-comparison.sqlite` has `think` and has no `num_thread` column. The request and sample tables match across all three files. The SQLite files were not rewritten. `load_experiment` now selects the columns the file has and leaves an absent column null. A stored think value of 0 still loads as false. The second launch exited 0 and wrote the findings file.

Notes that are not open problems: a request-throughput delta of exactly zero, or a P95 delta of exactly zero, leaves the sign sentence absent, and the test covers an unset side. The setting fields are in the required order, and the test checks `think` before `num_thread` and that matching concurrency stays off the list. The script's exits for a missing file, a missing match, and a match that is not unique were not executed. This run used the three files already on disk. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from the findings file. Day 2 through Day 10 notes were left as notes.

### Next steps

Day 12: routing fundamentals. Policy-based routing, workload-aware selection, constraints, latency budgets, and model capabilities stay on that day. Do not treat a Day 11 delta, phase label, or CPU sample as a recommendation. Do not copy a figure from `docs/analysis-findings.md` into `LEARN.md` or into a pytest assertion.

## 2026-11-23 — Day 12: Routing Fundamentals

### Five-line summary

Day 12 is routing fundamentals: three policies choose a model from a catalog the caller already filled. Nothing from earlier days failed, so there is no fix-first work. Static returns the configured model, workload-aware picks the lowest stored P95 for the requested profile, and latency-constrained adds the caller's budget as a filter. Fallback, live availability checks, and a routing experiment stay on Day 13. The day is done when mocked pytest passes and a decision names no winner.

### Completed

- Updated `docs/methodology.md` with a routing-selection section. It does not add a procedure step, and it does not rerun step 12. The caller supplies the catalog and the policy. Static returns the configured model and keeps that name when a constraint fails. Workload-aware selection is the lowest stored P95 for the requested profile among candidates that pass the capability and size filters. A miss returns no model. Latency-constrained adds the caller's budget as a further filter, then uses that same P95 rank. The text does not name a winner. Step 9 still waits. This day does not call Ollama. Availability-aware fallback, timeouts, and retries stay on Day 13.
- Pointed `docs/architecture.md` at `app/routing/policies.py` for static, workload-aware, and latency-constrained selection, and at `app/routing/router.py` for `route`. Removed the sentence that listed those three policies, plus availability-aware fallback, as later work. Availability-aware fallback stays later. Removed the claim that this day does not add routing. Routing does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. FastAPI and the five execution states stay out. The benchmark, metrics, optimization, and database boundaries stay as Day 11 wrote them.
- Recorded in `docs/metrics.md` that a latency budget reads a stored aggregate and is not a new latency formula, and that selection is not a percentile. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them. The percentile formula cell still says "P50 is the middle."
- Added `route(policy, catalog, request)` in `app/routing/router.py`. It dispatches to the three policies in `app/routing/policies.py`. An unknown policy name raises `ValueError`. Catalog entries are a sequence. A measurement holds `average_ms`, `median_ms`, `p50_ms`, `p95_ms`, and `p99_ms`, each present or unset. The router does not recompute them. The package does not import the adapter, the runner, the database, or `app.metrics`. It does not open a connection.
- Static returns the configured model name. A missing configured name raises `ValueError`. The decision keeps that name when a capability check, a size check, or a P95 check fails, and lists `capability`, `model_size`, and `p95_missing` in that order. A latency budget is ignored. A name absent from the catalog is still returned, with `in_catalog` false, `stored_p95_ms` unset, and an empty failure list. Static does not switch to another model.
- Workload-aware keeps candidates that have every required capability and that pass the size cap. Among those with a stored `p95_ms` for the requested profile, it selects the lowest P95. Equal P95 keeps the earlier catalog entry. A missing P95 is not selected. No eligible model returns no selected model and an empty failure list. A latency budget on the request is ignored.
- Latency-constrained uses those same filters, plus the caller's budget. The stored value must be present and less than or equal to the maximum. Among models that pass, the lowest stored P95 for that profile is selected. A missing budget, or a metric name outside the five latency fields, raises `ValueError`. No eligible model returns no selection.
- The decision is frozen. It holds `policy`, `selected_model` or unset, `in_catalog`, `stored_p95_ms` or unset, `failed_constraints`, and `reason`. The type has no field named winner, improved, recommendation, or best. The reason does not contain better, worse, improved, winner, recommend, or best. `app/routing/__init__.py` names `route` and the three policies.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/routing/__init__.py` (added)
- `app/routing/policies.py` (added)
- `app/routing/router.py` (added)
- `tests/unit/test_routing.py` (added)

### Test results

`python -m pytest`: 115 passed in 1.29s. Nineteen tests are new, and the existing 96 still pass. The run uses constructed catalogs, the existing mocks, and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not read a findings file for an expected timing. The figures 200, 500, 100, 900, 400, and 150 are fixtures.

### Problems

None left open.

Nothing failed in the suite, and no product fix was attempted. The first run of `python -m pytest` exited 0.

Notes that are not open problems: latency-constrained tests cover the budget and the P95 rank, and the capability and size filters are asserted on workload-aware. No test shows an unset budget field failing the budget, a latency-constrained miss, a missing P95 beside a present one, or an average equal to the maximum of 150. The static `vision` test checks that `capability` is in `failed_constraints`, and a separate test checks the full order when all three labels apply. The test name `test_required_vision_drops_the_faster_candidate_that_lacks_it` uses the word faster. The assertion checks the selected name and the stored P95. A string passed as capabilities raises `TypeError`. `TODAY.md` did not require that guard. `qwen3.5:2b` and `gemma3:1b` are not used as catalog names. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from a findings file. Day 2 through Day 11 notes were left as notes.

### Next steps

Day 13: routing reliability. Availability checks, timeouts, fallback, failure handling, cancellation, retries, and Experiment E stay on that day. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later. Do not treat a Day 12 selection as a recommendation. Do not copy a fixture duration into `LEARN.md` or into a pytest assertion.

## 2026-11-23 — Day 13: Routing Reliability

### Five-line summary

Day 13 is routing reliability: an availability-aware policy, the existing timeout, and no retry of the same model. Nothing from earlier days failed, so there is no fix-first work. A preferred model that is unavailable, or whose run fails before a successful measured row, is replaced once, and a cancelled run does not fall back. Experiment E runs `short_prompt_short_output` under the four policies against a `gemma3:1b` static baseline and writes findings from SQLite with no winner. The day is done when mocked pytest passes and the findings file matches the stored rows.

### Completed

- Updated `docs/methodology.md` so Day 13 adds availability-aware fallback beside the Day 12 selection rules. The caller supplies the catalog, the policy, and the unavailable set. Static, workload-aware, and latency-constrained stay as Day 12 wrote them and ignore that set. Availability-aware uses the workload-aware P95 rank as the preferred model, then selects the next eligible model when that preferred model is unavailable. A miss after that skip returns no model. `may_fallback` is true only when the measured rows have no success and no `CancelledError`. A cancelled run does not fall back. The same model is not retried. The retry count for this day is 0. The live script is the caller that may start one replacement run. The text does not name a winner. Step 9 still waits. This day runs Experiment E on `short_prompt_short_output` and still does not repeat an experiment for variance.
- Pointed `docs/architecture.md` at `app/routing/policies.py` for static, workload-aware, latency-constrained, and availability-aware selection, and at `app/routing/router.py` for `route`. Routing does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The live script is the caller that opens the database and calls `show_model`. FastAPI and the five execution states stay out. The benchmark, metrics, and optimization boundaries stay as Day 12 wrote them. The snapshot also stores `routing_policy`, `preferred_model`, `fallback_count`, and `retry_count`. An omitted value stays unset. A column that is absent from an older stored file loads as null. Load does not alter that file.
- Recorded in `docs/metrics.md` that a latency budget reads a stored aggregate and is not a new latency formula, that a fallback count is not a latency, and that the timeout this day records is the existing adapter error. Selection is not a percentile. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them. The percentile formula cell still says "P50 is the middle."
- Added `route(policy, catalog, request, unavailable=())`. It dispatches to the four policies. Only `availability_aware` reads the unavailable set. `Decision` gains `preferred_model`, `fell_back`, and `fallback_count`. The three existing policies keep `fell_back` false and `fallback_count` 0. With fixture P95 values of 200 ms and 500 ms, an empty unavailable set selects 200 ms. With the 200 ms model unavailable, availability-aware selects 500 ms once, `fell_back` is true, and `fallback_count` is 1. Static configured as `gemma` still returns `gemma` when that name is unavailable. An unknown policy name raises `ValueError`. The decision type has no winner field. The package does not import the adapter, the runner, the database, or `app.metrics`.
- Added `may_fallback`. It returns true only when the measured rows are non-empty, every row failed, and none has `error_type` `CancelledError`. A successful row returns false. A `CancelledError` row returns false. An empty tuple returns false. The helper does not import the runner.
- `ConfigurationSnapshot`, `build_snapshot`, and `ExperimentRow` gain `routing_policy`, `preferred_model`, `fallback_count`, and `retry_count`, each defaulting to unset. `save_experiment` writes them. `load_experiment` and `load_experiments` return them. A stored fallback count of 1 loads back as 1. A stored retry count of 0 loads back as 0. An omitted policy loads back as null. An older file whose experiments table lacks the new columns loads those fields as null. The load does not alter that file. `_SETTING_FIELDS` gains the four names after `python_version`. Matching values stay off the difference list. Null versus a set policy is a difference. The delta rule is unchanged. The comparison result still has no winner field. `app/benchmark/runner.py` and `app/inference/ollama.py` were not changed. The adapter timeout stays 120 seconds. The runner still does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`.
- Added `scripts/run_routing_experiment.py`. It inserts the project root on `sys.path` before importing `app`. It refuses to run if the adapter timeout is not 120 seconds. Before deleting any file, it calls `show_model` for `gemma3:1b` and `qwen3.5:2b` and loads `experiments/results/model-comparison.sqlite`. Each model has exactly one `short_prompt_short_output` row, with `average_ms` and `p95_ms` present. The catalog order is `qwen3.5:2b`, then `gemma3:1b`. The five stored latency fields are copied. Warm-up is 2. Measured calls are 3. Concurrency is 1. The static model is `gemma3:1b`. The latency budget is `average_ms` with maximum equal to that model's stored average. Required capabilities are empty. No size cap. The policies run in the order `static`, `workload_aware`, `latency_constrained`, `availability_aware`. Gemma's request omits `think`. A selected `qwen3.5:2b` would send `think` false. The script calls `summarize`, then `save_experiment`. Each saved run stores the policy, the preferred model, the fallback count, and `retry_count` 0. SQLite is `experiments/results/routing-effectiveness.sqlite`. `docs/routing-findings.md` was written from the experiments loaded back out. Static is the baseline for each `compare`. No model was downloaded. No installed model was marked unavailable.
- The live run stored four experiments. Each selected `gemma3:1b`. The stored fallback count is 0. The stored retry count is 0. Gemma's stored think flag is unset. No stored `error_type` was set. No second model was started. The findings file states that the timeout was the adapter default of 120 seconds, that the measured count is 3, that the retry count is 0, that thinking was not turned on, and that the file does not recommend a policy. A fresh load reproduced that file. No figure from that file was copied into `LEARN.md`, `PROGRESS.md`, or a pytest assertion. The three existing SQLite files were not rewritten.

### Files changed

- `docs/methodology.md` (updated)
- `docs/architecture.md` (updated)
- `docs/metrics.md` (updated)
- `app/routing/__init__.py` (updated)
- `app/routing/policies.py` (updated)
- `app/routing/router.py` (updated)
- `app/monitoring/snapshot.py` (updated)
- `app/database/models.py` (updated)
- `app/database/repository.py` (updated)
- `app/optimization/comparison.py` (updated)
- `tests/unit/test_routing.py` (updated)
- `tests/unit/test_database.py` (updated)
- `tests/unit/test_comparison.py` (updated)
- `tests/unit/test_routing_experiment.py` (added)
- `scripts/run_routing_experiment.py` (added)
- `experiments/results/routing-effectiveness.sqlite` (added)
- `docs/routing-findings.md` (added)

### Test results

`python -m pytest`: 135 passed in 1.39s. Twenty tests are new, and the existing 115 still pass. The run uses constructed catalogs, the in-memory database, the fake adapter, the fake clock, and the httpx mock transport. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not collect the live script, and it does not read `docs/routing-findings.md` for an expected timing. The figures 200 and 500 are fixtures. A fresh load of the four stored experiments reproduced the findings file. The three older SQLite hashes were the same before and after the script.

### Problems

None left open.

Nothing failed in the suite, and no product fix was attempted. The first run of `python -m pytest` exited 0. The first launch of `python scripts/run_routing_experiment.py` exited 0.

Notes that are not open problems: both models stayed available and every preferred run had a successful measured row, so the live second-model path did not run. No unit test drives the script loop that stores a failed run and calls `route` once more. An `OllamaError` from `engine_version` is caught by the same handler as a `show_model` failure before any row. `may_fallback` is tested with a lone success and with a cancelled row beside a failure. A success that follows a failed row is not a separate case. `build_snapshot`'s new arguments have no monitoring test. The stored rows show those fields were written. Qwen was not selected, so the live `think` false branch did not run. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a latency figure from the findings file. Day 2 through Day 12 notes were left as notes.

### Next steps

Day 14: the dashboard. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later. Do not treat a Day 13 selection, or a stored fallback count of 0, as a recommendation. Do not copy a figure from `docs/routing-findings.md` into `LEARN.md` or into a pytest assertion.


