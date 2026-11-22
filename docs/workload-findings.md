# Workload sensitivity findings

These figures were loaded from `experiments/results/workload-sensitivity.sqlite`.
This file describes the four stored summaries.
It does not recommend a profile, and it does not call one configuration an improvement.

The request timeout was the adapter default of 120 seconds.
The measured count is 3.
A timeout or other adapter error is listed as the stored `error_type`.
It was not retried.
Character length is the length of the stored prompt.
`prompt_eval_count` is the prompt length.
`eval_count` is the output length.
`num_predict` is the cap.
A longer cap is not proof the model emitted that many tokens.
A system CPU sample of 0 stays in the series.
It is a sample value.

## short_prompt_short_output

- Profile name: short_prompt_short_output
- Model: gemma3:1b
- Engine version: 0.40.17
- Character length: 36
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 32, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 32, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 32, error_type unset
- Average: 1904.21093333
- Median: 1865.8868
- P50: 1865.8868
- P95: 2010.3051
- P99: 2010.3051
- Generation throughput: 38.2296106254
- Request throughput: 0.525124052681
- Error rate: 0
- Sample count: 13
- Min system CPU percent: 11.7
- Max system CPU percent: 64.1
- Min system RAM used: 12749860864
- Max system RAM used: 13643096064
- Stored error_type values: none

## long_prompt_short_output

- Profile name: long_prompt_short_output
- Model: gemma3:1b
- Engine version: 0.40.17
- Character length: 1357
- num_predict: 32
- Measured success count: 3
- Measured row 1: prompt_eval_count 257, eval_count 32, error_type unset
- Measured row 2: prompt_eval_count 257, eval_count 32, error_type unset
- Measured row 3: prompt_eval_count 257, eval_count 32, error_type unset
- Average: 1894.0083
- Median: 1902.968
- P50: 1902.968
- P95: 1921.6352
- P99: 1921.6352
- Generation throughput: 37.4678113447
- Request throughput: 0.527953333994
- Error rate: 0
- Sample count: 10
- Min system CPU percent: 23.5
- Max system CPU percent: 64.5
- Min system RAM used: 13522186240
- Max system RAM used: 13565657088
- Stored error_type values: none

## short_prompt_long_output

- Profile name: short_prompt_long_output
- Model: gemma3:1b
- Engine version: 0.40.17
- Character length: 36
- num_predict: 128
- Measured success count: 3
- Measured row 1: prompt_eval_count 16, eval_count 93, error_type unset
- Measured row 2: prompt_eval_count 16, eval_count 99, error_type unset
- Measured row 3: prompt_eval_count 16, eval_count 100, error_type unset
- Average: 3754.33963333
- Median: 3693.5788
- P50: 3693.5788
- P95: 3918.8051
- P99: 3918.8051
- Generation throughput: 37.4638430613
- Request throughput: 0.266350107788
- Error rate: 0
- Sample count: 16
- Min system CPU percent: 19.3
- Max system CPU percent: 76.2
- Min system RAM used: 13526147072
- Max system RAM used: 13591224320
- Stored error_type values: none

## long_prompt_long_output

- Profile name: long_prompt_long_output
- Model: gemma3:1b
- Engine version: 0.40.17
- Character length: 1357
- num_predict: 128
- Measured success count: 3
- Measured row 1: prompt_eval_count 257, eval_count 60, error_type unset
- Measured row 2: prompt_eval_count 257, eval_count 57, error_type unset
- Measured row 3: prompt_eval_count 257, eval_count 88, error_type unset
- Average: 2885.93213333
- Median: 2658.285
- P50: 2658.285
- P95: 3347.9461
- P99: 3347.9461
- Generation throughput: 36.8991694735
- Request throughput: 0.346494915759
- Error rate: 0
- Sample count: 14
- Min system CPU percent: 26.7
- Max system CPU percent: 66.5
- Min system RAM used: 13543403520
- Max system RAM used: 13583855616
- Stored error_type values: none

