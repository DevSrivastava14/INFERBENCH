# InferBench

InferBench measures local LLM inference: client-observed latency, throughput, error rate, and CPU and RAM during a run. A stored number is a saved payload. This document is not a latency.

## Modules

The dashboard reads the API. It does not calculate TTFT, TPOT, percentiles, throughput, or error rate.

FastAPI in `app/main.py` and `app/api/` opens SQLite, calls `summarize`, and starts the runner. `job_status` is the API column. The five names are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED`. Request rows stay `success` and `error_type`. The runner does not set those five names.

`app/metrics/` owns the formulas. They are written in `docs/metrics.md`. This file does not change them. The adapter timeout stays 120 seconds. `think` true is rejected and does not start a job.

Ollama is the only adapter. llama.cpp is not built. CPU and RAM samples live in `app/monitoring/`. `app/optimization/` compares two stored experiments and does not name a winner. `app/routing/` selects from a catalog the caller already filled. It does not name a winner.

## Start

Use Python 3.13. From the repository root:

```text
python -m pip install -r requirements.txt
python -m app.main
```

`python -m app.main` listens on `127.0.0.1:8000` unless `INFERBENCH_HOST` and `INFERBENCH_PORT` are set. An absent variable keeps those defaults. An absent `OLLAMA_HOST` keeps `http://127.0.0.1:11434`. `.env.example` lists those names. Ollama stays on the host.

In `frontend/`:

```text
npm ci
npm run dev
```

`npm run dev` uses the Vite proxy, which stays `http://127.0.0.1:8000`.

Compose starts `api` and `web` only:

```text
docker compose up
```

The API publishes host port 8000. The dashboard publishes host port 8080. `OLLAMA_HOST` inside the API container is `http://host.docker.internal:11434`. Ollama stays on the host. Compose does not download a model.

## Demo

The path is the landing sentence, then Overview, Benchmark, History, Results, Comparisons, and Routing. A number on the screen is a stored payload. Walking these pages is not a new measurement.

The landing sentence is "An engineering platform for measuring local LLM inference performance." The name InferBench under that sentence opens the dashboard. Overview is `/overview`.

- Overview (`/overview`) shows engines, models, hardware, recent experiments, and the current CPU and RAM sample from the payload. A failed load says "The load failed." and does not invent a CPU sample or a model list. A stopped Ollama leaves Overview on that sentence.
- Benchmark (`/benchmark`) posts a run and shows the job state, the succeeded count, the failed count, and the latest CPU and RAM sample. `think` offers omitted and false. `think` true is not offered.
- History (`/history`) lists stored experiments, including the source file. A null `job_status` is a blank cell.
- Results (`/results`) lists the nine stored metrics and draws measured `end_to_end_ms` values it was given. No selected id passes no series.
- Comparisons (`/comparisons`) posts two stored pairs and shows the deltas, both phase labels, the differing snapshot fields, and the sign sentence only when the payload includes one.
- Routing (`/routing`) posts a policy and the catalog row entered on the form. It shows the selected model, the preferred model, the returned reason, the fallback count, and the failed constraints.

## Documentation

- [Architecture](docs/architecture.md)
- [Methodology](docs/methodology.md)
- [Metrics](docs/metrics.md)
- [Environment](docs/environment.md)

## Not run

Thinking on versus off, concurrency 8, `num_ctx`, a same-model quantization comparison, procedure step 9, CSV and JSON export, and llama.cpp were not run. Qwen versus Gemma is a cross-model comparison. Experiment G was not run.
