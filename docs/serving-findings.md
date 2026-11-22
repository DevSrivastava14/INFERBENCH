# Serving configuration findings

These figures were loaded from `experiments/results/serving-config.sqlite`.
This file describes the ten stored summaries.
It does not recommend a setting.
It does not recommend a thread count or a concurrency cap.
It does not call one configuration an improvement.

The request timeout was the adapter default of 120 seconds.
The measured count is 3.
Gemma's request does not send think.
Qwen was run with think false.
Thinking was not turned on.
Concurrency 8 and `num_ctx` were not varied.
A timeout or other adapter error is listed as the stored `error_type`.
It was not retried.
Character length is the length of the stored prompt.
`prompt_eval_count` is the prompt length.
`eval_count` is the output length.
`num_predict` is the cap.
The cap is not a token count.
TTFT is `ttft_ms` on the loaded row.
TPOT is `tpot_ms` on the loaded row.
A system CPU sample of 0 stays in the series.
It is a sample value.

## gemma3:1b / short_prompt_short_output / concurrency 1 / num_thread omitted

- Model: gemma3:1b
- Profile name: short_prompt_short_output
- Concurrency: 1
- num_thread: omitted
- Think: unset
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, TTFT 478.833, TPOT 26.9299935484, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, TTFT 519.9975, TPOT 27.0723903226, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, TTFT 492.8626, TPOT 27.0518225807, error_type unset
- Average: 1334.79116667
- Median: 1331.4691
- P50: 1331.4691
- P95: 1359.2416
- P99: 1359.2416
- Generation throughput: 38.2062119798
- Request throughput: 0.749153494009
- Error rate: 0
- Sample count: 9
- Min system CPU percent: 25.3
- Max system CPU percent: 57.6
- Min system RAM used: 11234533376
- Max system RAM used: 12113428480
- Stored error_type values: none

## gemma3:1b / short_prompt_short_output / concurrency 2 / num_thread omitted

- Model: gemma3:1b
- Profile name: short_prompt_short_output
- Concurrency: 2
- num_thread: omitted
- Think: unset
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, TTFT 2194.0088, TPOT 13.5945483871, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, TTFT 546.3497, TPOT 26.4098483871, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, TTFT 974.8162, TPOT 26.5849258064, error_type unset
- Average: 1926.48123333
- Median: 1798.9489
- P50: 1798.9489
- P95: 2615.4398
- P99: 2615.4398
- Generation throughput: 46.5055668617
- Request throughput: 0.853653438956
- Error rate: 0
- Sample count: 6
- Min system CPU percent: 34.2
- Max system CPU percent: 61.3
- Min system RAM used: 12113612800
- Max system RAM used: 12140797952
- Stored error_type values: none

## gemma3:1b / short_prompt_short_output / concurrency 4 / num_thread omitted

- Model: gemma3:1b
- Profile name: short_prompt_short_output
- Concurrency: 4
- num_thread: omitted
- Think: unset
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, TTFT 2914.7738, TPOT 26.1159451613, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, TTFT 835.6955, TPOT 26.2277290323, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, TTFT 1392.414, TPOT 26.1314354839, error_type unset
- Average: 2525.2039
- Median: 2202.4885
- P50: 2202.4885
- P95: 3724.3681
- P99: 3724.3681
- Generation throughput: 39.4618651223
- Request throughput: 0.80550577157
- Error rate: 0
- Sample count: 6
- Min system CPU percent: 39.7
- Max system CPU percent: 60
- Min system RAM used: 12120559616
- Max system RAM used: 12154695680
- Stored error_type values: none

## gemma3:1b / short_prompt_short_output / concurrency 1 / num_thread 4

- Model: gemma3:1b
- Profile name: short_prompt_short_output
- Concurrency: 1
- num_thread: 4
- Think: unset
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, TTFT 522.822499999, TPOT 27.9857806452, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, TTFT 493.1952, TPOT 28.0296612903, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, TTFT 468.1797, TPOT 27.6053516129, error_type unset
- Average: 1358.814
- Median: 1362.1147
- P50: 1362.1147
- P95: 1390.3817
- P99: 1390.3817
- Generation throughput: 37.0335422822
- Request throughput: 0.735913854513
- Error rate: 0
- Sample count: 9
- Min system CPU percent: 14.5
- Max system CPU percent: 40.1
- Min system RAM used: 11285745664
- Max system RAM used: 12157734912
- Stored error_type values: none

## gemma3:1b / short_prompt_short_output / concurrency 1 / num_thread 12

- Model: gemma3:1b
- Profile name: short_prompt_short_output
- Concurrency: 1
- num_thread: 12
- Think: unset
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, TTFT 508.2366, TPOT 30.4523354839, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, TTFT 557.4146, TPOT 27.4526870968, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, TTFT 495.231800001, TPOT 26.7539580645, error_type unset
- Average: 1395.1038
- Median: 1408.4479
- P50: 1408.4479
- P95: 1452.259
- P99: 1452.259
- Generation throughput: 36.5793938215
- Request throughput: 0.716772042909
- Error rate: 0
- Sample count: 9
- Min system CPU percent: 20.8
- Max system CPU percent: 94.3
- Min system RAM used: 11263688704
- Max system RAM used: 12108709888
- Stored error_type values: none

## qwen3.5:2b / short_prompt_short_output / concurrency 1 / num_thread omitted

- Model: qwen3.5:2b
- Profile name: short_prompt_short_output
- Concurrency: 1
- num_thread: omitted
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 32, TTFT 538.5781, TPOT 60.6151612904, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 32, TTFT 571.9873, TPOT 63.1175870968, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 32, TTFT 611.1236, TPOT 64.9274483871, error_type unset
- Average: 2523.38503333
- Median: 2528.6325
- P50: 2528.6325
- P95: 2623.8745
- P99: 2623.8745
- Generation throughput: 16.4145603922
- Request throughput: 0.396285866199
- Error rate: 0
- Sample count: 21
- Min system CPU percent: 16.2
- Max system CPU percent: 74.5
- Min system RAM used: 12078624768
- Max system RAM used: 14837891072
- Stored error_type values: none

## qwen3.5:2b / short_prompt_short_output / concurrency 2 / num_thread omitted

- Model: qwen3.5:2b
- Profile name: short_prompt_short_output
- Concurrency: 2
- num_thread: omitted
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 32, TTFT 3419.516, TPOT 52.0702354839, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 32, TTFT 670.6617, TPOT 62.3433290323, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 32, TTFT 2199.8208, TPOT 62.4572612903, error_type unset
- Average: 3924.33136667
- Median: 4135.9959
- P50: 4135.9959
- P95: 5033.6933
- P99: 5033.6933
- Generation throughput: 17.508677191
- Request throughput: 0.423603730797
- Error rate: 0
- Sample count: 12
- Min system CPU percent: 37.6
- Max system CPU percent: 73.3
- Min system RAM used: 14816530432
- Max system RAM used: 15037558784
- Stored error_type values: none

## qwen3.5:2b / short_prompt_short_output / concurrency 4 / num_thread omitted

- Model: qwen3.5:2b
- Profile name: short_prompt_short_output
- Concurrency: 4
- num_thread: omitted
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 32, TTFT 3374.6571, TPOT 60.0988774193, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 32, TTFT 1029.0413, TPOT 61.4146580645, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 32, TTFT 4675.88, TPOT 95.6305612903, error_type unset
- Average: 5270.34846667
- Median: 5237.7223
- P50: 5237.7223
- P95: 7640.4274
- P99: 7640.4274
- Generation throughput: 14.2613786861
- Request throughput: 0.360219496148
- Error rate: 0
- Sample count: 14
- Min system CPU percent: 27.4
- Max system CPU percent: 89.9
- Min system RAM used: 15020036096
- Max system RAM used: 15420555264
- Stored error_type values: none

## qwen3.5:2b / short_prompt_short_output / concurrency 1 / num_thread 4

- Model: qwen3.5:2b
- Profile name: short_prompt_short_output
- Concurrency: 1
- num_thread: 4
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 32, TTFT 805.856100001, TPOT 78.9496193548, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 32, TTFT 695.6031, TPOT 76.9057322581, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 32, TTFT 674.6253, TPOT 76.267116129, error_type unset
- Average: 3123.96033333
- Median: 3079.6808
- P50: 3079.6808
- P95: 3253.2943
- P99: 3253.2943
- Generation throughput: 13.3411221399
- Request throughput: 0.320100291262
- Error rate: 0
- Sample count: 23
- Min system CPU percent: 19
- Max system CPU percent: 59.3
- Min system RAM used: 11947696128
- Max system RAM used: 15358070784
- Stored error_type values: none

## qwen3.5:2b / short_prompt_short_output / concurrency 1 / num_thread 12

- Model: qwen3.5:2b
- Profile name: short_prompt_short_output
- Concurrency: 1
- num_thread: 12
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Logical CPU count: 12
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 32, TTFT 716.646, TPOT 77.6386516129, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 32, TTFT 793.9912, TPOT 76.7984322581, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 32, TTFT 673.801200001, TPOT 78.6228806451, error_type unset
- Average: 3136.43243333
- Median: 3123.4442
- P50: 3123.4442
- P95: 3174.7426
- P99: 3174.7426
- Generation throughput: 13.287456728
- Request throughput: 0.318826270417
- Error rate: 0
- Sample count: 21
- Min system CPU percent: 15.4
- Max system CPU percent: 100
- Min system RAM used: 11887570944
- Max system RAM used: 14893793280
- Stored error_type values: none

