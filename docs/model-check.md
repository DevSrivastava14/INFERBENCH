# InferBench live model check

This note compares the planning-time facts in `docs/environment.md` with live Ollama metadata. The read happened on 2026-11-19 against Ollama 0.40.16 at `http://127.0.0.1:11434`.

Calls made:

- `GET /api/tags`
- `POST /api/show` for `qwen3.5:2b`
- `POST /api/show` for `gemma3:1b`

No model was downloaded. No generate call was made. The thinking default comes from the show payload. A size or quantization label below is metadata. It is not a speed measurement, and Qwen versus Gemma is not a quantization comparison.

Each item is **verified**, **mismatch**, or **not present in the payload**. The raw field is the one Ollama returned. The planning wording is not copied onto a different label.

`GET /api/tags` also named `gemma4:31b-cloud` and `deepseek-v4.1-flash:cloud`. This check does not use those entries.

## `qwen3.5:2b`

| Item | Planning-time fact | Live field | Live value | Mark |
|---|---|---|---|---|
| Presence | Listed as installed | `GET /api/tags` `name` | `qwen3.5:2b` | verified |
| Parameter count | About 1.9 billion parameters | tags and show `details.parameter_size` | `1.9B` | verified |
| Parameter count | About 1.9 billion parameters | show `model_info` `general.parameter_count` | `1881825088` | verified |
| Parameter count | About 1.9 billion parameters | show `model_info` `general.size_label` | `1.9B` | verified |
| Quantization | Q8_0 | tags and show `details.quantization_level` | `Q8_0` | verified |
| Size | About 2.7 GB | tags `size` | `2683396812` bytes (2.683 GB, decimal) | verified |
| Size | About 2.7 GB | `POST /api/show` | no `size` field | not present in the payload |
| Thinking default | On by default | show `thinking` | `{"values": [false, true], "default": true}` | verified |

`1881825088` is 1.882 billion parameters. That agrees with "about 1.9 billion" and with the raw label `1.9B`. `2683396812` bytes is 2.683 decimal GB, which agrees with "about 2.7 GB". Show `model_info` also has `general.file_type` `7`. That integer is not the quantization label. The label used for the comparison is `quantization_level`.

Capabilities present on both tags and show: `completion`, `vision`, `tools`, `thinking`. The capability `thinking` says the server lists thinking for this model. The default itself is the `thinking.default` value above, which is `true`.

## `gemma3:1b`

| Item | Planning-time fact | Live field | Live value | Mark |
|---|---|---|---|---|
| Presence | Listed as installed | `GET /api/tags` `name` | `gemma3:1b` | verified |
| Parameter count | About 1 billion parameters | tags and show `details.parameter_size` | `999.89M` | verified |
| Parameter count | About 1 billion parameters | show `model_info` `general.parameter_count` | `999885952` | verified |
| Parameter count | About 1 billion parameters | show `model_info` `general.size_label` | `1B` | verified |
| Quantization | Q4_K_M | tags and show `details.quantization_level` | `Q4_K_M` | verified |
| Size | About 806 MB | tags `size` | `806067407` bytes (806.067 MB, decimal) | verified |
| Size | About 806 MB | `POST /api/show` | no `size` field | not present in the payload |
| Thinking default | Not a planning fact for this model | `POST /api/show` | no `thinking` field | not present in the payload |

`999885952` is 0.9999 billion parameters. The raw parameter label is `999.89M`, and `general.size_label` is `1B`. Those agree with "about 1 billion". `806067407` bytes is 806.067 decimal MB, which agrees with "about 806 MB". Show `model_info` also has `general.file_type` `15`. That integer is not the quantization label. The label used for the comparison is `quantization_level`.

Capabilities present on both tags and show: `completion`. That matches the planning note that this model supports completion. `vision` and `tools` are not in the capability list. This check does not add them from anywhere else.

## What was not contradicted

No planning-time fact in `docs/environment.md` was contradicted. That file still states the planning figures. This file holds the raw live fields.
