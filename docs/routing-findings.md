# Routing effectiveness findings

These figures were loaded from `experiments/results/routing-effectiveness.sqlite`.
This file describes the stored summaries.
The static experiment is the baseline for each comparison.
A delta is the candidate's stored aggregate minus the baseline's stored aggregate.
The request timeout was the adapter default of 120 seconds.
The measured count is 3.
The retry count is 0.
Gemma's request does not send think.
Qwen was run with think false when Qwen was selected.
Thinking was not turned on.
A pair whose models differ is a cross-model comparison.
This file does not name a winner.
This file does not recommend a policy.
It does not call a policy an improvement.

The fallback count is 0.

## static / gemma3:1b / experiment 1

- Routing policy: static
- Selected model: gemma3:1b
- Preferred model: gemma3:1b
- Fallback count: 0
- Retry count: 0
- Think: unset
- Measured count: 3
- Error rate: 0
- Average: 1376.58846666
- Median: 1372.4904
- P50: 1372.4904
- P95: 1388.8291
- P99: 1388.8291
- Generation throughput: 36.8152013034
- Request throughput: 0.726401520911
- Stored error_type values: none

## workload_aware / gemma3:1b / experiment 2

- Routing policy: workload_aware
- Selected model: gemma3:1b
- Preferred model: gemma3:1b
- Fallback count: 0
- Retry count: 0
- Think: unset
- Measured count: 3
- Error rate: 0
- Average: 1355.21103334
- Median: 1340.9571
- P50: 1340.9571
- P95: 1385.1176
- P99: 1385.1176
- Generation throughput: 37.2852688931
- Request throughput: 0.737870932945
- Stored error_type values: none

## latency_constrained / gemma3:1b / experiment 3

- Routing policy: latency_constrained
- Selected model: gemma3:1b
- Preferred model: gemma3:1b
- Fallback count: 0
- Retry count: 0
- Think: unset
- Measured count: 3
- Error rate: 0
- Average: 1365.77156667
- Median: 1357.3406
- P50: 1357.3406
- P95: 1386.2626
- P99: 1386.2626
- Generation throughput: 37.38079469
- Request throughput: 0.732165724248
- Stored error_type values: none

## availability_aware / gemma3:1b / experiment 4

- Routing policy: availability_aware
- Selected model: gemma3:1b
- Preferred model: gemma3:1b
- Fallback count: 0
- Retry count: 0
- Think: unset
- Measured count: 3
- Error rate: 0
- Average: 1382.8743
- Median: 1378.2026
- P50: 1378.2026
- P95: 1406.4795
- P99: 1406.4795
- Generation throughput: 37.0327936962
- Request throughput: 0.723109318004
- Stored error_type values: none

## Comparison against static / workload_aware

- Baseline experiment id: 1
- Candidate experiment id: 2
- Baseline model: gemma3:1b
- Candidate model: gemma3:1b
- Candidate preferred model: gemma3:1b
- Candidate fallback count: 0
- Baseline average_ms: 1376.58846666
- Candidate average_ms: 1355.21103334
- average_ms delta: -21.3774333291
- Baseline median_ms: 1372.4904
- Candidate median_ms: 1340.9571
- median_ms delta: -31.5332999962
- Baseline p50_ms: 1372.4904
- Candidate p50_ms: 1340.9571
- p50_ms delta: -31.5332999962
- Baseline p95_ms: 1388.8291
- Candidate p95_ms: 1385.1176
- p95_ms delta: -3.7114999941
- Baseline p99_ms: 1388.8291
- Candidate p99_ms: 1385.1176
- p99_ms delta: -3.7114999941
- Baseline error_rate: 0
- Candidate error_rate: 0
- error_rate delta: 0
- Baseline generation_throughput_tps: 36.8152013034
- Candidate generation_throughput_tps: 37.2852688931
- generation_throughput_tps delta: 0.470067589657
- Baseline request_throughput_rps: 0.726401520911
- Candidate request_throughput_rps: 0.737870932945
- request_throughput_rps delta: 0.0114694120335
- Sign sentence: Request throughput is higher and P95 is lower.

## Comparison against static / latency_constrained

- Baseline experiment id: 1
- Candidate experiment id: 3
- Baseline model: gemma3:1b
- Candidate model: gemma3:1b
- Candidate preferred model: gemma3:1b
- Candidate fallback count: 0
- Baseline average_ms: 1376.58846666
- Candidate average_ms: 1365.77156667
- average_ms delta: -10.8168999989
- Baseline median_ms: 1372.4904
- Candidate median_ms: 1357.3406
- median_ms delta: -15.1497999977
- Baseline p50_ms: 1372.4904
- Candidate p50_ms: 1357.3406
- p50_ms delta: -15.1497999977
- Baseline p95_ms: 1388.8291
- Candidate p95_ms: 1386.2626
- p95_ms delta: -2.56649999938
- Baseline p99_ms: 1388.8291
- Candidate p99_ms: 1386.2626
- p99_ms delta: -2.56649999938
- Baseline error_rate: 0
- Candidate error_rate: 0
- error_rate delta: 0
- Baseline generation_throughput_tps: 36.8152013034
- Candidate generation_throughput_tps: 37.38079469
- generation_throughput_tps delta: 0.565593386538
- Baseline request_throughput_rps: 0.726401520911
- Candidate request_throughput_rps: 0.732165724248
- request_throughput_rps delta: 0.00576420333708
- Sign sentence: Request throughput is higher and P95 is lower.

## Comparison against static / availability_aware

- Baseline experiment id: 1
- Candidate experiment id: 4
- Baseline model: gemma3:1b
- Candidate model: gemma3:1b
- Candidate preferred model: gemma3:1b
- Candidate fallback count: 0
- Baseline average_ms: 1376.58846666
- Candidate average_ms: 1382.8743
- average_ms delta: 6.2858333331
- Baseline median_ms: 1372.4904
- Candidate median_ms: 1378.2026
- median_ms delta: 5.71219999983
- Baseline p50_ms: 1372.4904
- Candidate p50_ms: 1378.2026
- p50_ms delta: 5.71219999983
- Baseline p95_ms: 1388.8291
- Candidate p95_ms: 1406.4795
- p95_ms delta: 17.6504000046
- Baseline p99_ms: 1388.8291
- Candidate p99_ms: 1406.4795
- p99_ms delta: 17.6504000046
- Baseline error_rate: 0
- Candidate error_rate: 0
- error_rate delta: 0
- Baseline generation_throughput_tps: 36.8152013034
- Candidate generation_throughput_tps: 37.0327936962
- generation_throughput_tps delta: 0.217592392721
- Baseline request_throughput_rps: 0.726401520911
- Candidate request_throughput_rps: 0.723109318004
- request_throughput_rps delta: -0.00329220290674
- Sign sentence: Request throughput is lower and P95 is higher.

