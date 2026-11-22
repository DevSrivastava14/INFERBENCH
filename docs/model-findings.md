# Model comparison findings

These figures were loaded from `experiments/results/model-comparison.sqlite`.
This file is a cross-model comparison.
Experiment G was not run.
Thinking on versus off was not run.
It does not recommend a model.
It does not attribute a difference to Q8 versus Q4.
It does not call one configuration an improvement.

The request timeout was the adapter default of 120 seconds.
The measured count is 3.
A timeout or other adapter error is listed as the stored `error_type`.
It was not retried.
Character length is the length of the stored prompt.
`prompt_eval_count` is the prompt length.
`eval_count` is the output length.
`num_predict` is the cap.
A longer cap is not proof the model emitted that many tokens.
TTFT is `ttft_ms` on the loaded row.
TPOT is `tpot_ms` on the loaded row.
A system CPU sample of 0 stays in the series.
It is a sample value.

## qwen3.5:2b / short_prompt_short_output

- Model: qwen3.5:2b
- Profile name: short_prompt_short_output
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 32, TTFT 1093.1694, TPOT 61.0569677419, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 32, TTFT 1093.8125, TPOT 61.7347935484, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 32, TTFT 1044.0023, TPOT 62.6489290323, error_type unset
- Average: 2993.2152
- Median: 2986.1191
- P50: 2986.1191
- P95: 3007.5911
- P99: 3007.5911
- Generation throughput: 16.6995398268
- Request throughput: 0.334073123417
- Error rate: 0
- Sample count: 24
- Min system CPU percent: 17.1
- Max system CPU percent: 71.2
- Min system RAM used: 12672376832
- Max system RAM used: 15659819008
- Stored error_type values: none

## qwen3.5:2b / long_prompt_short_output

- Model: qwen3.5:2b
- Profile name: long_prompt_short_output
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Character length: 1357
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 259, eval_count 32, TTFT 1303.0857, TPOT 69.1720612903, error_type unset
- Measured row 2: prompt_eval_count 259, eval_count 32, TTFT 1133.8716, TPOT 67.3063709678, error_type unset
- Measured row 3: prompt_eval_count 259, eval_count 32, TTFT 1357.9844, TPOT 71.8542258064, error_type unset
- Average: 3417.75136667
- Median: 3447.4196
- P50: 3447.4196
- P95: 3585.4654
- P99: 3585.4654
- Generation throughput: 14.8645643094
- Request throughput: 0.292577681642
- Error rate: 0
- Sample count: 20
- Min system CPU percent: 35.6
- Max system CPU percent: 90.5
- Min system RAM used: 14291156992
- Max system RAM used: 16525549568
- Stored error_type values: none

## qwen3.5:2b / short_prompt_long_output

- Model: qwen3.5:2b
- Profile name: short_prompt_long_output
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Character length: 36
- num_predict: 128
- Measured success count: 3
- Measured row 1: prompt_eval_count 19, eval_count 128, TTFT 1199.2922, TPOT 72.8764874016, error_type unset
- Measured row 2: prompt_eval_count 19, eval_count 78, TTFT 840.2104, TPOT 79.5478857143, error_type unset
- Measured row 3: prompt_eval_count 19, eval_count 58, TTFT 764.5406, TPOT 75.1787894737, error_type unset
- Average: 7489.91176667
- Median: 6965.3976
- P50: 6965.3976
- P95: 10454.6061
- P99: 10454.6061
- Generation throughput: 13.4243940492
- Request throughput: 0.133511539195
- Error rate: 0
- Sample count: 36
- Min system CPU percent: 25.5
- Max system CPU percent: 77.5
- Min system RAM used: 14258597888
- Max system RAM used: 14457069568
- Stored error_type values: none

## qwen3.5:2b / long_prompt_long_output

- Model: qwen3.5:2b
- Profile name: long_prompt_long_output
- Think: false
- Quantization: Q8_0
- Parameter size: 1.9B
- Size in bytes: 2683396812
- Architecture: qwen35
- Engine version: 0.40.17
- Character length: 1357
- num_predict: 128
- Measured success count: 3
- Measured row 1: prompt_eval_count 259, eval_count 35, TTFT 718.8475, TPOT 78.3763735294, error_type unset
- Measured row 2: prompt_eval_count 259, eval_count 40, TTFT 761.8634, TPOT 74.0290717949, error_type unset
- Measured row 3: prompt_eval_count 259, eval_count 34, TTFT 742.9273, TPOT 72.7088878788, error_type unset
- Average: 3391.654
- Median: 3383.6442
- P50: 3383.6442
- P95: 3648.9972
- P99: 3648.9972
- Generation throughput: 13.7084091582
- Request throughput: 0.294832705977
- Error rate: 0
- Sample count: 18
- Min system CPU percent: 29.1
- Max system CPU percent: 65.8
- Min system RAM used: 14267621376
- Max system RAM used: 14316548096
- Stored error_type values: none

## gemma3:1b / short_prompt_short_output

- Model: gemma3:1b
- Profile name: short_prompt_short_output
- Think: null
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, TTFT 681.9681, TPOT 33.1452870968, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, TTFT 678.880400001, TPOT 33.7954193548, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, TTFT 704.0182, TPOT 33.6290129032, error_type unset
- Average: 1727.50933333
- Median: 1726.5384
- P50: 1726.5384
- P95: 1746.5176
- P99: 1746.5176
- Generation throughput: 30.7923121732
- Request throughput: 0.578848002561
- Error rate: 0
- Sample count: 11
- Min system CPU percent: 13.2
- Max system CPU percent: 59.4
- Min system RAM used: 14334287872
- Max system RAM used: 15175163904
- Stored error_type values: none

## gemma3:1b / long_prompt_short_output

- Model: gemma3:1b
- Profile name: long_prompt_short_output
- Think: null
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Character length: 1357
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 257, eval_count 32, TTFT 642.796800001, TPOT 34.2639935484, error_type unset
- Measured row 2: prompt_eval_count 257, eval_count 32, TTFT 574.5242, TPOT 34.8827483871, error_type unset
- Measured row 3: prompt_eval_count 257, eval_count 32, TTFT 653.8644, TPOT 35.7209193548, error_type unset
- Average: 1707.36096667
- Median: 1704.9806
- P50: 1704.9806
- P95: 1761.2129
- P99: 1761.2129
- Generation throughput: 29.5303066307
- Request throughput: 0.585677731336
- Error rate: 0
- Sample count: 12
- Min system CPU percent: 33.2
- Max system CPU percent: 66.5
- Min system RAM used: 15096156160
- Max system RAM used: 15139045376
- Stored error_type values: none

## gemma3:1b / short_prompt_long_output

- Model: gemma3:1b
- Profile name: short_prompt_long_output
- Think: null
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Character length: 36
- num_predict: 128
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 128, TTFT 692.5031, TPOT 37.1744125984, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 95, TTFT 640.7462, TPOT 35.5868606383, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 104, TTFT 647.7543, TPOT 36.0627029126, error_type unset
- Average: 4587.2591
- Median: 4362.2127
- P50: 4362.2127
- P95: 5413.6535
- P99: 5413.6535
- Generation throughput: 27.7570903514
- Request throughput: 0.217992423194
- Error rate: 0
- Sample count: 22
- Min system CPU percent: 38.7
- Max system CPU percent: 63.3
- Min system RAM used: 15008407552
- Max system RAM used: 15107129344
- Stored error_type values: none

## gemma3:1b / long_prompt_long_output

- Model: gemma3:1b
- Profile name: long_prompt_long_output
- Think: null
- Quantization: Q4_K_M
- Parameter size: 999.89M
- Size in bytes: 806067407
- Architecture: gemma3
- Engine version: 0.40.17
- Character length: 1357
- num_predict: 128
- Measured success count: 3
- Measured row 1: prompt_eval_count 257, eval_count 81, TTFT 715.348299999, TPOT 36.442775, error_type unset
- Measured row 2: prompt_eval_count 257, eval_count 78, TTFT 625.8311, TPOT 38.081112987, error_type unset
- Measured row 3: prompt_eval_count 257, eval_count 55, TTFT 624.1963, TPOT 36.4022037037, error_type unset
- Average: 3259.58746667
- Median: 3558.0768
- P50: 3558.0768
- P95: 3630.7703
- P99: 3630.7703
- Generation throughput: 27.3888914266
- Request throughput: 0.30678102959
- Error rate: 0
- Sample count: 16
- Min system CPU percent: 41.2
- Max system CPU percent: 66
- Min system RAM used: 14920609792
- Max system RAM used: 14997995520
- Stored error_type values: none

