# InferBench Day 1 self-check

Answers for the Day 1 checks. Sources are `LEARN.md`, `docs/metrics.md`, `docs/architecture.md`, and `docs/environment.md`. No application code was written. No answer below is a measured InferBench benchmark.

## 1. Prefill and decode

Prefill reads the whole prompt and fills the KV cache the model will reuse. Decode then generates one new token at a time, and each new token depends on the tokens already produced. The wait before the first token is mostly prefill. Time per output token is a decode story.

Source: `LEARN.md`, Prefill and decode, and KV cache.

## 2. TTFT

TTFT uses the client clock. The formula is time of first generated content minus request start time. The unit is milliseconds. Server-reported `prompt_eval_duration` stays in its own field and is not copied into TTFT.

Source: `docs/metrics.md`, Time to first token, and `LEARN.md`, TTFT, TPOT, and end-to-end latency.

## 3. TPOT

TPOT is decode duration divided by (output tokens − 1). Decode duration is the client-observed time from the first generated content until the request finishes. The output-token count comes from provider metadata or a compatible tokenizer. It does not come from the number of HTTP stream chunks. A chunk is a piece of the response body, not one token. If the count is approximate, the result is labeled an estimate.

Source: `docs/metrics.md`, Time per output token, and `LEARN.md`, Tokens.

## 4. Qwen versus Gemma

`qwen3.5:2b` versus `gemma3:1b` is a cross-model comparison. The two models differ in architecture, parameter count, and quantization. A quantization comparison needs compatible variants of the same model. Reporting Qwen versus Gemma as a quantization result is forbidden. The sizes and quantization labels in the environment note are planning-time facts. Day 2 must re-check them against live Ollama. They are not measured InferBench results.

Source: `docs/environment.md`, Which experiment is forbidden, and `LEARN.md`, Parameters and quantization.

## 5. Owners

Percentile calculation belongs to the metrics engine. The metrics engine also owns P50, P95, and P99, and it does not call Ollama. The Ollama HTTP stream belongs to the inference adapter. The adapter records the client timestamp of the first generated content and the provider metadata. It does not compute percentiles.

Source: `docs/architecture.md`, Responsibilities and Who owns the two easy-to-mix jobs.

## 6. Teaching numbers

Every number in `LEARN.md` is an illustration. The file says so at the top: the examples are made-up teaching examples, not measured InferBench results. The worked TTFT and TPOT walk-through, the five-latency percentile example, and the sentences about concurrency on this CPU are illustrations of the question. They are not results. InferBench may report a speed or a latency only after a real run.
