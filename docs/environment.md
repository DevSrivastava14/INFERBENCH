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
