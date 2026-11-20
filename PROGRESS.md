## 2026-11-12 — Day 1: LLM Inference Fundamentals

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
