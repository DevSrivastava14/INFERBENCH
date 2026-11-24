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

## 2026-11-23 — Day 14: Frontend Development

### Five-line summary

Day 14 is the dashboard shell: a React and JavaScript workbench with overview, configuration, results, and history. Nothing from earlier days failed, so there is no fix-first work. The screens show empty states in one layout, and fixture numbers stay inside frontend tests. The type, color, and spacing are specified so the tool does not look like a generic AI template, and FastAPI stays on Day 15. The day is done when pytest stays green and the frontend tests and production build pass with no measurement on the open pages.

### Completed

- Updated `docs/architecture.md` so `frontend/` reads measurements it is given. The dashboard does not calculate TTFT, TPOT, percentiles, throughput, or error rate. It does not call Ollama, does not call `psutil`, does not open SQLite, and does not call `summarize`. The four pages are Overview, Benchmark configuration, Results, and Experiment history. FastAPI and the five execution states stay out. The benchmark, metrics, optimization, routing, monitoring, and database boundaries stay as Day 13 wrote them. A chart draws a series it is given. A chart is not a new latency formula. Selection is not a percentile.
- Updated `docs/methodology.md` so Day 14 adds no procedure step, does not rerun step 12, and does not repeat an experiment for variance. The text does not name a winner. Step 9 still waits. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later. `docs/metrics.md` was not edited. The percentile formula cell still says "P50 is the middle."
- Added a Vite, React, and JavaScript app. One shell wraps the four routes. The rail carries the product name, InferBench. UI text uses IBM Plex Sans. Metric names and field names use IBM Plex Mono. The tokens are one ink, one paper, and one muted accent. Hand-written CSS in `frontend/src/styles/` is the look. Below 720px the rail collapses, the history table scrolls, and the form stays one column.
- Overview has five regions: inference engines, models, hardware, recent experiments, and current CPU and RAM. Each says nothing is loaded. The page does not name Ollama as up, does not list `gemma3:1b` or `qwen3.5:2b`, and does not show a CPU percent. `loadExperiments()` returns `[]` and does not call `fetch`.
- The configuration form keeps local state for model, prompt, profile name, `num_predict`, warm-up count, measured count, concurrency, `think`, and `num_thread`. The profile control offers the four Day 8 names, or blank. `think` defaults to omitted. A blank `num_thread` stays blank and is not stored as 0, because this form does not store anything. Streaming is a label for the benchmark path the runner already uses. There is no Run control and no `num_ctx`.
- History renders configuration column headers and an empty body. Results lists TTFT, TPOT, end-to-end latency, generation throughput, request throughput, P50, P95, P99, and error rate, and says no experiment is selected. `SeriesChart` draws the `series` prop it receives and does not compute a percentile. The Results page passes no series. A frontend test supplies 100, 110, and 120 ms. Those numbers are a fixture. The runner still does not set `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`.

### Files changed

- `docs/architecture.md` (updated)
- `docs/methodology.md` (updated)
- `frontend/package.json` (added)
- `frontend/package-lock.json` (added)
- `frontend/vite.config.js` (added)
- `frontend/index.html` (added)
- `frontend/.gitignore` (added)
- `frontend/src/main.jsx` (added)
- `frontend/src/App.jsx` (added)
- `frontend/src/layout/Shell.jsx` (added)
- `frontend/src/styles/tokens.css` (added)
- `frontend/src/styles/layout.css` (added)
- `frontend/src/pages/Overview.jsx` (added)
- `frontend/src/pages/Benchmark.jsx` (added)
- `frontend/src/pages/History.jsx` (added)
- `frontend/src/pages/Results.jsx` (added)
- `frontend/src/services/experiments.js` (added)
- `frontend/src/components/SeriesChart.jsx` (added)
- `frontend/src/components/SeriesChart.test.jsx` (added)
- `frontend/src/pages/Overview.test.jsx` (added)
- `frontend/src/pages/Benchmark.test.jsx` (added)
- `frontend/src/pages/History.test.jsx` (added)
- `frontend/src/pages/Results.test.jsx` (added)
- `frontend/src/test-setup.js` (added)

### Test results

`python -m pytest`: 135 passed in 1.58s. The count is the Day 13 count. Pytest collected only `tests/unit/` and did not collect `frontend/`. The run does not contact Ollama. No test asserts a latency number from a live server. Pytest does not read a findings file for an expected timing.

`npm test`: 6 passed. The chart test sees 100, 110, and 120. The Results page render does not include that series. Overview, history, and the configuration form render no latency, no CPU sample, and no discovered model list. The form does not call `fetch`. Frontend tests do not read a findings file.

`npm run build` succeeded. Vite reports the script chunk is 680 kB because Recharts is included. The build exits 0.

### Problems

None left open.

The first frontend run failed one chart test. `draws nothing when no series is passed` found the text 100. That text was left in the document by the previous test. The chart container for the empty call had no SVG. `frontend/src/test-setup.js` now cleans up after each test. The second run passed.

The first view of the dev server was a blank page. `useMatches` in the shell requires a data router in React Router 7, and `BrowserRouter` is not one. The shell threw, and React left the root empty. The app now uses `createBrowserRouter` and `RouterProvider`. The extra `BrowserRouter` in `main.jsx` was removed. After that change, Overview rendered its five empty regions. The frontend suite was run again and passed.

Notes that are not open problems: the narrow layout is in the CSS and was not opened in a narrow window, and no test checks that width. The open screens are plainer than the professional-UI section. That density stays for later, after the dashboard is connected and during the engineering polish. The `think` control can hold `true` in local state. The default is omitted, and the form does not send it. History's column names are the runner's configuration fields. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from a findings file. Day 2 through Day 13 notes were left as notes.

### Next steps

Day 15: connect the dashboard to FastAPI. Benchmark execution, live progress, results retrieval, experiment comparisons, and routing visualization stay on that day. Do not treat an empty screen, or the fixture series 100, 110, and 120, as a benchmark result. Thinking on versus off, concurrency 8, `num_ctx`, and a same-model quantization run stay later.

## 2026-11-24 — Day 15: Backend and Frontend Integration

### Five-line summary

Day 15 connects the dashboard to FastAPI so a run, a stored result, a comparison, and a routing decision show in the same workbench. Nothing from earlier days failed, so there is no fix-first work. A benchmark job uses the five states, request rows stay success and error_type, and the start call returns before the run finishes. The screen reads what the API returns and does not compute a metric or name a winner. The day is done when pytest and the frontend tests pass without contacting Ollama, and a started job can be watched until it is stored.

### Completed

- Updated `docs/architecture.md` so `app/main.py` and `app/api/` open SQLite, call `summarize`, and start the runner. FastAPI owns the connection. `job_status` is the API column. The five names are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED`. Request rows stay `success` and `error_type`. The runner does not set those five names. The dashboard reads the API. It still does not calculate TTFT, TPOT, percentiles, throughput, or error rate, and it still does not call Ollama, `psutil`, or SQLite. Comparisons and Routing join the shell. `job_status` is nullable. Load leaves it null when the column is absent and does not alter the file. The benchmark, metrics, optimization, routing, monitoring, and database calculation boundaries stay as Day 14 wrote them, aside from that load.
- Updated `docs/methodology.md` so Day 15 adds no procedure step, does not rerun step 12, and does not repeat an experiment for variance. The text does not name a winner. Step 9 still waits. Thinking on versus off, a concurrency-8 sweep, `num_ctx`, and a same-model quantization run stay later. A job state is not a latency. `docs/metrics.md` was not edited. The percentile formula cell still says "P50 is the middle."
- Added FastAPI and uvicorn. The request schemas use the Pydantic that FastAPI already installs. `POST /api/jobs` stores `PENDING` and returns the id without awaiting `generate_stream`. The task sets `RUNNING`, reads the engine version, fills the hardware snapshot, and then starts the runner. A failure on that read sets `FAILED` and does not call `generate_stream`. A finished run stores the real snapshot and calls `summarize`. A raised run stores the sink rows and samples with null aggregates and sets `FAILED`. A set cancel event sets `CANCELLED` and stores the rows the runner returned. The stored retry count is 0. The task runs the one submitted model. `think` true is rejected and stores no job. `qwen3.5:2b` sends `think` false. `gemma3:1b` omits `think`. Blank warm-up, measured count, and concurrency use 2, 3, and 1. Blank `num_thread` stays unset. `num_ctx` is not a field.
- New runs use `experiments/results/dashboard.sqlite`. History reads that file and then the four existing result files. Those four stay read-only. A missing result file contributes no rows and is not created. Each history item carries its source and its id. Overview returns engines, models, hardware, recent experiments, and the probe sample. One experiment returns the stored snapshot, rows, samples, and aggregates. Compare loads two source-and-id pairs and returns `compare`, including the sign sentence only when `compare` stored one. Route returns the decision from `route`. Compare and route do not call Ollama. Their JSON has no winner, improved, recommendation, or best field.
- The dashboard proxies `/api` to `http://127.0.0.1:8000`. Overview, History, Results, and the run form render the payloads. A failed overview load says the load failed and does not invent a CPU sample or a model list. A payload CPU sample of 0 is shown. History renders the source, and a null `job_status` is a blank cell. Results lists the nine metrics from the stored summary and passes measured `end_to_end_ms` values to the existing chart. No selected id passes no series. Run posts the runner fields and polls while the job is `PENDING` or `RUNNING`. The page shows the state, the succeeded count, the failed count, and the latest CPU and RAM sample. The think control offers omitted and false. Comparisons posts two stored pairs and renders the deltas, both phase labels, the differing snapshot fields, and the sign sentence when the payload includes one. Routing posts a policy and one catalog row. The latency fields in that row are the values entered on the form. The page shows the selected model, the preferred model, the returned reason, the fallback count, and the failed constraints.

### Files changed

- `requirements.txt` (updated)
- `docs/architecture.md` (updated)
- `docs/methodology.md` (updated)
- `app/benchmark/runner.py` (updated)
- `app/database/models.py` (updated)
- `app/database/repository.py` (updated)
- `app/main.py` (added)
- `app/api/__init__.py` (added)
- `app/api/schemas.py` (added)
- `app/api/routes.py` (added)
- `app/api/service.py` (added)
- `tests/unit/test_api.py` (added)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_database.py` (updated)
- `frontend/vite.config.js` (updated)
- `frontend/src/services/experiments.js` (updated)
- `frontend/src/App.jsx` (updated)
- `frontend/src/layout/Shell.jsx` (updated)
- `frontend/src/layout/Shell.test.jsx` (added)
- `frontend/src/styles/layout.css` (updated)
- `frontend/src/pages/Overview.jsx` (updated)
- `frontend/src/pages/Overview.test.jsx` (updated)
- `frontend/src/pages/Benchmark.jsx` (updated)
- `frontend/src/pages/Benchmark.test.jsx` (updated)
- `frontend/src/pages/History.jsx` (updated)
- `frontend/src/pages/History.test.jsx` (updated)
- `frontend/src/pages/Results.jsx` (updated)
- `frontend/src/pages/Results.test.jsx` (updated)
- `frontend/src/pages/Comparisons.jsx` (added)
- `frontend/src/pages/Comparisons.test.jsx` (added)
- `frontend/src/pages/Routing.jsx` (added)
- `frontend/src/pages/Routing.test.jsx` (added)

### Test results

`python -m pytest`: 150 passed in 10.83s. Twelve tests are new in `tests/unit/test_api.py`, and three more cover the progress sink and a stored `job_status`. The earlier 135 still pass. The run uses a fake adapter and a temporary database. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not read a findings file for an expected timing.

`npm test`: 19 passed. The chart test sees 100, 110, and 120. The Results page render with no selected experiment does not include that series. Overview, history, the configuration form, Comparisons, and Routing render from mocked `fetch` payloads. A mocked overview failure shows the load-failed sentence and no invented CPU sample or model list. Frontend tests do not read a findings file.

`npm run build` succeeded. Vite reports the script chunk is 696 kB because Recharts is included. The build exits 0.

### Problems

None left open.

The first frontend run failed one Results test. `shows stored values and the measured series for the selected id` looked up the text 15 and found two nodes: the stored end-to-end value, and a chart axis tick for the series 40 and 50. The page was already drawing the stored summary and the measured series. The assertion now reads those summary numbers from the metric list. The next frontend run passed.

Notes that are not open problems: the routing form posts one catalog row, so a second stored model cannot be entered there. The narrow layout and the plainer screens stay Day 14 notes. The percentile formula cell was left as it stands. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from a findings file. Installing FastAPI also upgraded `typing-extensions` and `typing-inspection` in the environment. Those upgrades were left in place. Day 2 through Day 14 notes were left as notes.

### Next steps

Day 16: testing and failure injection. Do not treat a dashboard payload, the fixture series 100, 110, and 120, a stored fallback count of 0, or a figure in an existing findings file as a new benchmark result. Thinking on versus off, concurrency 8, `num_ctx`, a same-model quantization run, CSV and JSON export, and procedure step 9 stay later.

## 2026-11-24 — Day 16: Testing and Failure Injection, and an explanatory dashboard

### Five-line summary

Day 16 locks the failure cases the suite did not assert, and makes the dashboard say what each clock and control means. Nothing from earlier days failed, so there is no fix-first work. The new tests use fakes and do not contact Ollama, and a timeout row can still sit inside a completed job. The type, the rail, and the label sentences make a demo understandable without naming a winner or painting a fixture latency. After that review, the site opens on one purpose sentence and then replaces itself with the existing dashboard.

### Completed

- A database error returns HTTP 500 `{"detail": "database error"}` and invents no summary and no latency. A timeout or a malformed response on one call is one request row, and the job can still finish `COMPLETED`. A missing model, and any other raised run, is `FAILED` and does not call `generate_stream`.
- Added the remaining failure cases with a fake adapter, a fake clock, and a temporary database. A mixed run reloads the failed row and the successful rows, and load does not recompute the summary. A successful row with no first-content stamp leaves TTFT unset. A missing `eval_count` leaves TPOT unset. A cancelled row still sets the request-throughput window. Adapter failures alone leave the five latency fields unset. Generation throughput stays unset when no measured row qualifies. A stored `sampling_error` loads back as that error. `sample_interval` of 0 is rejected. `may_fallback` is false when a success follows a failure. `engine_version` rejects a non-JSON body and records a connection failure. The formulas stay as Day 6 wrote them. `docs/metrics.md` was not edited.
- Added `tests/integration/`. One test holds the fake stream, sees `RUNNING`, then `COMPLETED`, and the reloaded aggregates match the job. A second ends `CANCELLED`. A third uses a missing model and never calls `generate_stream`. The client uses the app in-process. It does not start a live server and does not contact Ollama.
- The shell uses IBM Plex Sans and IBM Plex Mono, a dark rail, one accent, and a type scale for the product name, page title, lede, section title, body, caption, and metric value. Each page has a lede. Benchmark fields, history columns, the nine result metrics, and the four routing policies keep their technical names and gain one sentence. Those sentences do not contain better, worse, improved, winner, recommend, or best. `think` true is still not offered.
- The site root now states "An engineering platform for measuring local LLM inference performance." and then opens Overview. The name InferBench under that sentence links to the same dashboard. Overview moved to `/overview`.
- The live check flagged long hardware lines spilling their columns, two Routing captions with one word on the last line, and a warm paper background on every page. The metric grid now wraps those lines, captions and ledes use a wrap that keeps the last word with the line above, and the content surface is a light green-gray taken from the rail. A fresh check of the six dashboard routes, at a desktop width and a phone width, came back clear.
- Installed the design hook and recorded code-first for landing pages and showcase surfaces. The doctor report is clear.

### Files changed

- `app/main.py` (updated)
- `docs/architecture.md` (updated)
- `docs/methodology.md` (updated)
- `tests/unit/test_api.py` (updated)
- `tests/unit/test_benchmark.py` (updated)
- `tests/unit/test_database.py` (updated)
- `tests/unit/test_latency.py` (updated)
- `tests/unit/test_ollama.py` (updated)
- `tests/unit/test_routing.py` (updated)
- `tests/unit/test_statistics.py` (updated)
- `tests/unit/test_throughput.py` (updated)
- `tests/integration/test_job_path.py` (added)
- `frontend/src/copy.js` (added)
- `frontend/src/App.jsx` (updated)
- `frontend/src/layout/Shell.jsx` (updated)
- `frontend/src/services/experiments.js` (updated)
- `frontend/src/styles/tokens.css` (updated)
- `frontend/src/styles/layout.css` (updated)
- `frontend/src/styles/landing.css` (added)
- `frontend/src/pages/Landing.jsx` (added)
- `frontend/src/pages/Landing.test.jsx` (added)
- `frontend/src/pages/Overview.jsx` (updated)
- `frontend/src/pages/Overview.test.jsx` (updated)
- `frontend/src/pages/Benchmark.jsx` (updated)
- `frontend/src/pages/Benchmark.test.jsx` (updated)
- `frontend/src/pages/Results.jsx` (updated)
- `frontend/src/pages/Results.test.jsx` (updated)
- `frontend/src/pages/History.jsx` (updated)
- `frontend/src/pages/History.test.jsx` (updated)
- `frontend/src/pages/Comparisons.jsx` (updated)
- `frontend/src/pages/Comparisons.test.jsx` (updated)
- `frontend/src/pages/Routing.jsx` (updated)
- `frontend/src/pages/Routing.test.jsx` (updated)
- `PRODUCT.md` (added)

### Test results

`python -m pytest`: 167 passed in 4.03s. Seventeen tests are new: three API cases, two latency, two throughput, one statistics, two database, one benchmark, one routing, two Ollama, and three integration. The earlier 150 still pass. The run uses fakes and a temporary database. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not read a findings file for an expected timing.

`npm test`: 20 passed. One test is new: the landing sentence, then Overview. The chart test sees 100, 110, and 120. The Results page render with no selected experiment does not include that series, and it includes the TTFT definition. Overview, history, the configuration form, Comparisons, and Routing render from mocked `fetch` payloads. A mocked overview failure shows the load-failed sentence and no invented CPU sample or model list. Frontend tests do not read a findings file.

`npm run build` succeeded. The CSS is 11.28 kB. The script chunk is 704.04 kB because Recharts is included. The build exits 0.

### Problems

None left open.

The first collection of `tests/integration/test_job_path.py` raised `NameError: pytest is not defined` on the asyncio marker. The module imported `pytest`, and the three tests passed. A PowerShell `&&` between `npm test` and `npm run build` was not a valid separator, so the two commands were run in sequence. Both succeeded. The first landing test advanced fake timers outside `act`, so the route never left the purpose sentence. Wrapping the advance in `act` made the test see Overview.

Notes that are not open problems: the five job-status colors are in the stylesheet, and no element sets them yet. The shell has a lede slot, and the pages render their own ledes. No frontend test clicks Cancel. `engine_version` has a connection-failure test and no separate timeout test. The percentile formula cell still says "P50 is the middle." `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today. Day 2 through Day 15 notes were left as notes.

### Next steps

Day 17: Docker, CI, and reproducibility. Do not treat a dashboard payload, the fixture series 100, 110, and 120, a stored fallback count of 0, or a figure in an existing findings file as a new benchmark result. Thinking on versus off, concurrency 8, `num_ctx`, a same-model quantization run, CSV and JSON export, and procedure step 9 stay later.

## 2026-11-24 — Day 17: Docker, CI, and reproducibility

### Five-line summary

Day 17 pins the libraries already on this machine, packs the API and the dashboard into Compose, and lists the existing checks in GitHub Actions. Nothing from earlier days failed, so there is no fix-first work. Ollama stays on the host that already has the models, and the containers do not download one. Pytest and the frontend tests use the same fakes as Day 16, and a built image is not a measured latency. The workflow file is in the tree. It has not run on GitHub yet.

### Completed

- Pinned the versions already installed. `requirements.txt` pins httpx 0.28.1, psutil 7.2.2, sqlalchemy 2.0.43, fastapi 0.141.1, and uvicorn 0.52.4. `requirements-dev.txt` pins pytest 8.4.2 and pytest-asyncio 1.4.0. No package was upgraded on this machine. The API image installs `requirements.txt` only.
- `app/main.py` reads `INFERBENCH_HOST` and `INFERBENCH_PORT`. An absent or blank variable keeps `127.0.0.1` and `8000`. `.env.example` shows those defaults, and `OLLAMA_HOST` as `http://127.0.0.1:11434`. The container is the caller that sets the host to `0.0.0.0`. The laptop default stays `127.0.0.1`. The root `.gitignore` ignores `.env`, virtualenvs, `__pycache__`, and frontend build output. It does not ignore `experiments/results/*.sqlite` or `.env.example`.
- Added the API image from `python:3.13-slim` and the dashboard image. The dashboard image runs `npm ci` from the lockfile on Node 24.19.0, and Nginx serves the production build and proxies `/api` to the `api` service. The browser still uses relative `/api` URLs. The Vite dev proxy stays `http://127.0.0.1:8000`.
- `docker-compose.yml` starts `api` and `web` only. `OLLAMA_HOST` for `api` is `http://host.docker.internal:11434`. Compose adds `host-gateway`. `experiments/results` is a mount, so `dashboard.sqlite` persists on the host and the four older result files stay there. `.dockerignore` keeps those SQLite files out of the build. A missing result file is still not created. There is no Ollama service and no model pull. The API publishes host port 8000. The dashboard publishes host port 8080.
- Added `.github/workflows/ci.yml` with three jobs and no secrets. Python 3.13 installs both requirements files and runs `python -m pytest`. Node 24.19.0, in `frontend/`, runs `npm ci`, `npm test`, and `npm run build`. The image job runs `docker compose build`. It does not start the stack and it does not contact Ollama.
- Updated `docs/environment.md`, `docs/architecture.md`, and `docs/methodology.md`. Day 17 adds no procedure step, does not rerun step 12, and does not repeat an experiment for variance. The text does not name a winner. Step 9 still waits. A container is not a latency. The formulas stay as Day 6 wrote them. `docs/metrics.md` was not edited. The percentile formula cell still says "P50 is the middle." The timeout stays 120 seconds. `think` true is still rejected.

### Files changed

- `requirements.txt` (updated)
- `requirements-dev.txt` (updated)
- `app/main.py` (updated)
- `.env.example` (added)
- `.gitignore` (added)
- `docs/environment.md` (updated)
- `docs/architecture.md` (updated)
- `docs/methodology.md` (updated)
- `Dockerfile` (added)
- `frontend/Dockerfile` (added)
- `frontend/nginx.conf` (added)
- `docker-compose.yml` (added)
- `.dockerignore` (added)
- `.github/workflows/ci.yml` (added)
- `tests/unit/test_listen.py` (added)

### Test results

`python -m pytest`: 172 passed in 7.29s. Five tests are new. The earlier 167 still pass. The run uses a mapping for the listen address, the workflow file, a fake adapter, a fake clock, and a temporary database. It does not contact Ollama. No test asserts a latency number from a live server. Pytest does not read a findings file for an expected timing.

`npm test`: 20 passed. The chart test sees 100, 110, and 120. The Results page render with no selected experiment does not include that series. Overview, history, the configuration form, Comparisons, and Routing render from mocked `fetch` payloads. Frontend tests do not read a findings file.

`npm run build` succeeded. The CSS is 11.28 kB. The script chunk is 704.04 kB because Recharts is included. The build exits 0.

`docker compose config` is valid. `docker compose build` exited 0. Both images built. That exit is a build check. It is not a measurement. The stack was not started.

### Problems

None left open.

The first `npm test`, started at the same time as pytest, failed two tests at the 5-second limit: `the landing states the purpose and then opens Overview` and `the rail links Comparisons and Routing`. Both raised `TestTimeoutError`. The pages and those tests were not edited. `npm test` was run again by itself and passed 20 tests. `npm run build` was then run and exited 0.

Notes that are not open problems: the `python:3.13-slim` tag contains Python 3.13.18. This laptop's interpreter stays 3.13.5. Compose publishes the dashboard on host port 8080, which `TODAY.md` does not name, and publishes the API on host port 8000, which is also the local server's port. The workflow has not run on GitHub. No running container was asked to serve a page or proxy `/api`. The new tests pass a mapping and read the workflow file. They do not use a fake adapter, a fake clock, or a temporary database, because this code does not run a benchmark. `LEARN.md` and `docs/day1-check.md` were already modified in the working tree. They were not edited today, and they do not hold a figure from a findings file. Day 2 through Day 16 notes were left as notes.

### Next steps

Day 18: documentation and final validation. The README stays on that day. Do not treat a built image, or a green CI log, as a benchmark result. Thinking on versus off, concurrency 8, `num_ctx`, a same-model quantization run, CSV and JSON export, and procedure step 9 stay later.


