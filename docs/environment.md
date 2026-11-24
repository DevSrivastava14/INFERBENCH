# InferBench environment and comparison rules

This note records the machine and the local models as they stood at planning time. Day 1 does not download models and does not run a benchmark.

## Machine

Development is CPU-only, on Windows.

| Component | Planning-time fact |
|---|---|
| CPU | Intel Core i5-13420H, 13th generation |
| RAM | About 15.7 GB |
| GPU | Intel UHD integrated graphics |
| Dedicated NVIDIA GPU | None |

The core system is not designed around CUDA. The platform should detect hardware, monitor CPU and RAM, report GPU capabilities when they exist, and keep working when no dedicated GPU is present. It should avoid large model downloads and avoid loading several memory-heavy models at once.

A model-card context length is not proof that this machine can serve that context. The KV cache grows with context and with concurrent requests, and this machine has about 15.7 GB of RAM. The context length that matters is the one a run actually uses.

## Local models

Ollama is already installed. These notes are planning-time facts, not fresh measurements. Every size, parameter count, and quantization label below is a planning-time fact.

### `qwen3.5:2b`

- About 1.9 billion parameters.
- Quantization: Q8_0.
- About 2.7 GB.
- Thinking is on by default in the current configuration. Thinking can be disabled. That fact is recorded here so later benchmarks do not ignore it. Day 1 does not benchmark thinking mode.

### `gemma3:1b`

- About 1 billion parameters.
- Quantization: Q4_K_M.
- About 806 MB.
- Supports completion.

## Live check

Day 2 read live Ollama metadata and compared it with the planning-time facts above. The raw fields and the mark for each item are in `docs/model-check.md`. No fact in this file was contradicted, so the figures above stay as planning-time facts. They are still not measured InferBench results. A live size or quantization label is metadata, not a speed.

## Which experiment is forbidden

Comparing `qwen3.5:2b` with `gemma3:1b` is a cross-model comparison. It is allowed later as Experiment B, and the write-up must say that the models differ in architecture, parameter count, and quantization.

A quantization experiment is forbidden unless the two sides are compatible variants of the same model. Qwen versus Gemma must not be reported as a quantization result.

Cloud-hosted Ollama models are not suitable for the core local benchmarks. Do not download additional models without a specific experimental reason. Day 1 downloads nothing.

## Pinned dependencies

Day 17 pins the libraries already installed on this machine. Pinning records those versions. It does not upgrade them. The interpreter already recorded is Python 3.13.5. A pin is not a latency.

| Package | Pinned version | File |
|---|---|---|
| httpx | 0.28.1 | `requirements.txt` |
| psutil | 7.2.2 | `requirements.txt` |
| sqlalchemy | 2.0.43 | `requirements.txt` |
| fastapi | 0.141.1 | `requirements.txt` |
| uvicorn | 0.52.4 | `requirements.txt` |
| pytest | 8.4.2 | `requirements-dev.txt` |
| pytest-asyncio | 1.4.0 | `requirements-dev.txt` |

`requirements-dev.txt` is for local pytest. Those two pins are not in `requirements.txt`.

## Listen address

`app/main.py` reads `INFERBENCH_HOST` and `INFERBENCH_PORT` from the environment. An absent or blank variable keeps `127.0.0.1` and `8000`. `.env.example` shows those defaults, and `OLLAMA_HOST` as `http://127.0.0.1:11434`. The laptop default stays `127.0.0.1`. The container is the caller that sets `INFERBENCH_HOST` to `0.0.0.0`. A container is not a latency.

The root `.gitignore` ignores `.env`, virtualenvs, `__pycache__`, and frontend build output. It does not ignore `experiments/results/*.sqlite` or `.env.example`.

## Images and Compose

`Dockerfile` builds the API from `python:3.13-slim`, installs `requirements.txt`, and sets `INFERBENCH_HOST` to `0.0.0.0`. `frontend/Dockerfile` installs the dashboard from the lockfile with the Node 24.19.0 already on this machine, then Nginx serves that production build and proxies `/api` to the `api` service. `docker-compose.yml` starts `api` and `web` only. `OLLAMA_HOST` for `api` is `http://host.docker.internal:11434`. Compose adds `host-gateway` so that name resolves. `experiments/results` is a mount. The image build does not copy the SQLite files in. A missing result file is still not created. There is no Ollama service and no model pull. The Vite dev proxy stays `http://127.0.0.1:8000`. A built image is not a latency.

## GitHub Actions

`.github/workflows/ci.yml` has three jobs and no secrets. The Python 3.13 job installs `requirements.txt` and `requirements-dev.txt`, then runs `python -m pytest`. The Node 24.19.0 job, in `frontend/`, runs `npm ci`, `npm test`, and `npm run build`. The image job runs `docker compose build`. It does not start the stack and it does not contact Ollama. No job reads a findings file for an expected timing. A green job is not a latency.

Day 17 adds no procedure step, does not rerun step 12, and does not repeat an experiment for variance. The text does not name a winner. Step 9 still waits. The latency, throughput, percentile, and error-rate formulas stay as Day 6 wrote them.
