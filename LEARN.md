# InferBench — Day 1 Concepts

These notes explain how a local language model produces text, and which facts InferBench has to measure correctly. Every number below is an **illustration**. It is a made-up teaching example. It is not a measured InferBench result.

## Inference versus training

Training is the long job that sets a model’s weights. Inference is what happens afterward: the finished model reads a prompt and predicts the next tokens.

**Illustration.** The prompt is “The capital of France is”. Inference continues the text with something like “Paris”. InferBench would time that continuation. It would not change the model’s weights.

**Why it matters.** InferBench is a benchmarking tool for local serving. It measures how fast and how heavy inference is. Training foundation models is outside the project.

## Prefill and decode

A generation request has two phases.

**Prefill** reads the whole prompt and fills the cache the model will reuse. The wait before the first token mostly comes from this phase. Longer prompts make prefill more expensive.

**Decode** produces the answer one new token at a time. Each token depends on the tokens already produced. Longer answers make decode take longer.

**Illustration.** A 2,000-token prompt with a 20-token answer spends most of the wait in prefill. A 20-token prompt with a 500-token answer spends most of the time in decode.

**Why it matters.** Experiment C changes prompt length and output length separately so those two costs can be seen apart. Time to first token is mostly a prefill story. Time per output token is a decode story.

## Tokens

The model does not read letters or words as a person does. A tokenizer turns text into token ids, and the model predicts those ids.

**Illustration.** The word “benchmark” might be one token, or it might be split into more than one, depending on the tokenizer. The name “InferBench” might become “Infer” plus “Bench”. A limit of “100 tokens” is not a limit of 100 words.

**Why it matters.** Output limits, time per output token, and throughput all count tokens. InferBench must take the count from provider metadata or a compatible tokenizer. An HTTP streaming chunk is a piece of the response body. It is not automatically one token.

## KV cache

While decoding, the model needs the earlier tokens. It stores their key and value tensors in a cache. The next token can read that cache instead of redoing the whole prefix.

**Illustration.** While writing token 100, a model without a cache would reprocess tokens 1 through 99. With a cache, it computes token 100 and reads the stored keys and values for the earlier tokens.

**Why it matters.** The cache grows with context length and with the number of requests in flight. This machine has about 15.7 GB of RAM and no dedicated NVIDIA GPU. Concurrency levels 1, 2, 4, and 8 have to stay inside that memory. InferBench records RAM so a run that is swapping or failing is visible.

## Context length

Context length is the maximum number of tokens the model can hold for one request. That budget covers the prompt, the generated output, and any special tokens.

**Illustration.** A model card might advertise a 32,000-token context. Filling that much cache on this CPU laptop can still be impractical, because the cache consumes RAM. The useful context for an experiment is the length that actually runs.

**Why it matters.** InferBench must record the context setting used in the run. A number from a model card is not proof that this machine can serve that context.

## Parameters and quantization

Parameters are the learned weights. More parameters usually mean a larger model and more memory.

Quantization stores those weights with fewer bits. Q8 uses more bits per weight than Q4. Fewer bits usually means a smaller file, less RAM, and often faster inference, with some loss of quality.

**Illustration, from the planning notes, not from a new measurement.**

- `qwen3.5:2b` is about 1.9 billion parameters, Q8_0, about 2.7 GB. Thinking is on by default in the current setup.
- `gemma3:1b` is about 1 billion parameters, Q4_K_M, about 806 MB.

Comparing Q8 and Q4 of the **same** model would be a quantization experiment. Comparing Qwen3.5 2B with Gemma3 1B changes architecture, parameter count, and quantization together. That is a cross-model comparison.

**Why it matters.** Experiment B may compare these two local models as they are. Experiment G, a controlled quantization study, waits until compatible variants of one model are available. Day 2 must read the live model metadata from Ollama. The sizes above are planning-time facts.

## TTFT, TPOT, and end-to-end latency

These three clocks are client-observed. They use the benchmark process’s own timestamps.

- **Time to first token (TTFT)** = time of the first generated content − request start time.
- **Time per output token (TPOT)** = decode duration / (output tokens − 1).
- **End-to-end latency** = request completion time − request start time.

Decode duration is the time after the first generated content until the request finishes. TPOT needs a real output-token count. If the count is approximate, the result must be labeled as an estimate.

**Illustration.** Request start is 0 ms. The first generated text arrives at 800 ms. The request finishes at 3,000 ms. The provider reports 21 output tokens.

- TTFT = 800 ms.
- Decode duration = 3,000 − 800 = 2,200 ms.
- TPOT = 2,200 / (21 − 1) = 110 ms.
- End-to-end latency = 3,000 ms.

Ollama can also return server fields such as `prompt_eval_count`, `prompt_eval_duration`, `eval_count`, and `eval_duration`. Those describe work inside the server. InferBench keeps them beside the client clocks and does not copy one into the other.

**Why it matters.** Interactive use cares about TTFT. Long answers care about TPOT. End-to-end latency is the full wait the client saw, including everything around the model call. Mixing a server duration into TTFT would make every later experiment incomparable.

## Throughput, percentiles, and error rate

- **Generation throughput** = output tokens / decode duration.
- **Request throughput** = completed requests / measurement duration.
- **Error rate** = failed requests / total requests.

**Percentiles** describe the spread of latency. P50 is the middle request. P95 is a slow request: about 95 percent of requests were faster. P99 is slower still. An average can hide those slow requests.

**Illustration.** Five end-to-end latencies, in milliseconds: 100, 110, 120, 130, and 2,000. The average is about 492 ms. The median (P50) is 120 ms. The average is pulled up by one slow request. P95 and P99 exist so that slow tail stays visible.

Warm-up requests, with a starting policy of 2–3, let the model finish loading before the measured window. A starting point for measured repetitions is 3–5 when the machine can afford them. Warm-up requests stay out of the measured aggregates.

**Why it matters.** Experiment A needs request throughput, generation throughput, P50, P95, P99, and the failure rate together. A higher request rate with a much worse P95 is a real finding. InferBench may report it only after measuring it.

## Bottlenecks on this machine

Prefill is heavy work over the prompt. Decode is sequential: the next token waits for the previous one, and on a CPU it is often limited by how fast memory can feed the weights.

This computer is an Intel Core i5-13420H with about 15.7 GB of RAM, Intel UHD graphics, and no NVIDIA GPU. Extra concurrent requests share that one CPU and that one memory bus.

**Illustration.** One request might finish in a few seconds. Eight requests at once might each take much longer, because they wait on the same hardware. Throughput might rise a little while P95 latency rises a lot. Those sentences describe the question. They are not a result.

**Why it matters.** Experiment A asks whether more concurrency improves throughput or mainly adds queueing on CPU-only hardware. The answer waits for a real run. CUDA-style assumptions do not apply here.

## Where each idea lands in the architecture

InferBench splits the work so a timing bug and a serving bug are not the same module.

| Module | Owns | Does not own |
|---|---|---|
| Inference adapter | Model discovery, HTTP calls, streaming and non-streaming responses, provider metadata, error normalization | Percentiles or throughput summaries |
| Workload engine | Prompts, output limits, concurrency, warm-up, repetitions, cancellation, status | The latency formulas |
| Metrics engine | TTFT, TPOT, end-to-end latency, throughput, percentiles, error rate | Calls to Ollama |
| Optimization | Comparisons and recommendations grounded in stored measurements | Invented speedups |
| Routing | Model choice from availability, workload, and measured latency | Hardcoded guesses presented as measured policy |
| Database | Experiment config, model metadata, request rows, aggregates, errors, hardware snapshot | Live metric math |
| Monitoring | CPU and RAM samples during a run, system and process where possible | Token timing |

The dashboard shows stored measurements. Future benchmark runs use the states `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED`. The runner must not block the FastAPI event loop. None of that runtime is built on Day 1.

**Illustration.** A streaming response arrives chunk by chunk. The Ollama adapter records the client timestamp of the first generated content and stores `eval_count` from the final metadata. The metrics engine then computes TTFT and TPOT from those records. The adapter does not publish P95. The metrics engine does not open an HTTP connection.

**Why it matters.** If chunk counts leak into TPOT, or server durations leak into TTFT, every experiment after Day 1 is wrong. The module split is what keeps those clocks apart.

# InferBench — Day 2 Concepts

These notes explain how InferBench talks to a local Ollama server. Every number below is an **illustration**. It is a made-up teaching example. It is not a measured InferBench result.

Day 1 concepts — prefill, decode, tokens, the KV cache, quantization, TTFT, and TPOT — are kept in this file, above. The same notes are also in `docs/day1-concepts.md`.

## What Ollama is in this project

Ollama is a local HTTP server. It loads the model weights and runs inference. InferBench is a client of that server. The model does not run inside the adapter process.

**Illustration.** A request to `http://127.0.0.1:11434` asks the server already running on this machine to use `gemma3:1b`. The adapter sends HTTP and reads HTTP. The weights stay in the Ollama process.

**Why it matters.** Only the inference adapter may open that connection. The metrics module stays on stored records. A timing bug and a serving bug stay in different modules, which is the split written down on Day 1.

## The HTTP API used today

Three calls cover Day 2.

- `GET /api/tags` lists the models stored on this machine. Each entry can carry a name, a size in bytes, and detail fields such as parameter size and quantization.
- `POST /api/show` returns one model's metadata: the same sort of detail, plus parameters and any capability list the server includes.
- `POST /api/generate` asks that model for text. `stream: false` returns one JSON object. `stream: true` returns a series of lines.

**Illustration.** A tags response that includes `gemma3:1b` and a size in bytes is a discovery result. It says the model file is present. It says nothing about how fast the model answers.

**Why it matters.** Day 2 uses these payloads to check the planning-time facts in `docs/environment.md`. Parameter count, quantization, and size become project facts only after this live read. Until that read, they stay planning-time notes.

## Discovery versus a model card

The show payload is the record for this machine. A model card is a publisher's description. InferBench writes down fields Ollama returned.

**Illustration.** A model card might advertise a 32,000-token context. The Day 2 check still records only the fields in `/api/tags` and `/api/show`. A context length that never appears in those payloads stays off the check.

**Why it matters.** This computer has about 15.7 GB of RAM and no dedicated NVIDIA GPU. A card length is not proof that this CPU can serve that context. The same rule covers vision, tools, and completion: record a capability when the payload contains it, and leave it out when the payload does not.

## Streaming and non-streaming

A non-streaming generate call comes back as one JSON object. The text and the final metadata arrive together.

A streaming call comes back as NDJSON: one JSON object per line. Content lines carry pieces of the text. The last line carries the provider metadata, including `eval_count` and `prompt_eval_count`.

**Illustration.** A stream has four body lines. The last line says `eval_count` is 2. The HTTP line count is 4. The output-token count from the provider is 2. Day 2 keeps both numbers and treats `eval_count` as the provider's token count.

**Why it matters.** Time per output token, on Day 5, divides by an output-token count from provider metadata or a compatible tokenizer. A body line is a piece of the response. Using the line count would make every later TPOT wrong.

## Inference settings

A generate call names the model and the prompt. It sets `stream` to true or false. An options object can include `num_predict`, which caps how many tokens the server may generate. When the API accepts a think flag, the request may carry one.

**Illustration.** A connection smoke sets `num_predict` to 8 and uses a tiny prompt. The cap keeps the call short. The call proves the adapter can send the body and read the reply. The elapsed time of that call is not an InferBench result.

**Why it matters.** Later experiments change prompt length, output length, and thinking on purpose. The Qwen thinking default has to be read from `/api/show`. A smoke generate does not decide that default. If the show payload has no thinking field, the check says the field is absent.

## Errors the adapter must keep apart

Four failures are different outcomes.

- **Unavailable.** The connection fails, or the server does not answer. Ollama is down.
- **Model not installed.** The server answers, and the named model is absent.
- **Malformed response.** The body is not the JSON the adapter expects.
- **Timeout.** The wait exceeds the limit set for the call.

**Illustration.** Connection refused on port 11434 is unavailable. Turning that failure into an empty model list would look like a machine with no models installed. Day 2 raises the unavailable error so the two cases stay apart.

**Why it matters.** Discovery is how InferBench learns which models it can benchmark. Collapsing these cases hides the cause. The adapter also does not retry. A hidden retry would change how long a later benchmark appears to take. PLAN.md requires any retry policy to be explicit and recorded before it exists.

## Server duration fields

Ollama can return `prompt_eval_duration` and `eval_duration` on the final metadata object, next to `prompt_eval_count` and `eval_count`. Those durations describe work inside the server. Client TTFT and end-to-end latency stay on the benchmark process's own timestamps. Day 2 does not compute those client clocks.

Ollama's API description documents the duration fields in nanoseconds. The figure below uses that documented unit as a teaching example. `docs/metrics.md` states the unit as a project fact only after Day 2 reads a live final metadata object and the description agrees.

**Illustration.** A field value of 1100000000, read as nanoseconds, is 1.1 seconds of server time. That 1.1 seconds is server work. It is not client TTFT, and it is not end-to-end latency.

**Why it matters.** Mixing a server duration into TTFT would make every later experiment incomparable. The adapter stores the raw fields. On a later day, the metrics module computes TTFT and TPOT from client timestamps on stored records.
