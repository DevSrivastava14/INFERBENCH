# Failures the suite already locks

These notes describe behavior the tests already lock. They cite the tests. They do not quote a latency. A document is not a latency.

## One failed call can still finish

A timeout on one call is one request row, and the job can still finish `COMPLETED`. `tests/unit/test_api.py` locks that in `test_timeout_on_one_call_completes_and_stores_the_other_rows` and in `test_request_error_still_completes`. The row's `error_type` is `OllamaTimeoutError`.

A malformed response on one call is one request row, and the job can still finish `COMPLETED`. `tests/unit/test_api.py` `test_malformed_response_on_one_call_still_completes` locks that. The row's `error_type` is `MalformedResponseError`.

## A raised run is failed

A missing model is `FAILED` and does not call `generate_stream`. `tests/unit/test_api.py` `test_version_failure_and_missing_model_do_not_stream` locks the missing model and the other raised run that suite covers before the runner starts: a failure while reading the engine version. That version failure is also `FAILED` and does not call `generate_stream`. `tests/integration/test_job_path.py` `test_missing_model_never_calls_generate_stream` locks the missing model on the in-process client. `tests/unit/test_benchmark.py` `test_missing_model_causes_zero_stream_calls` locks the runner: `show_model` raises before any stream call.

## Cancel

Cancel stores `CANCELLED`. `tests/unit/test_api.py` `test_cancel_ends_cancelled` and `tests/integration/test_job_path.py` `test_cancel_ends_cancelled` lock that status. A cancelled run does not fall back. `tests/unit/test_routing.py` `test_may_fallback_is_false_for_a_cancelled_row` locks that. The same model is not retried. `tests/unit/test_benchmark.py` `test_cancel_signal_records_each_started_attempt_once` records each started attempt once. The retry count for that path is 0. `test_cancel_ends_cancelled` in `tests/unit/test_api.py` locks `retry_count` 0.

## A database error invents nothing

A database error returns HTTP 500 `{"detail": "database error"}` and invents no summary and no latency. `tests/unit/test_api.py` `test_database_error_returns_no_invented_summary` locks that body.

## Two columns

Request rows stay `success` and `error_type`. `job_status` is the API column. The five names are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED`. The runner does not set those five names.

`tests/unit/test_api.py` `test_blocked_run_is_running_then_completed_with_aggregates` locks `PENDING`, `RUNNING`, and `COMPLETED` on the API, and it locks that `request_rows` has no `job_status` column. `FAILED` is locked by `test_version_failure_and_missing_model_do_not_stream`. `CANCELLED` is locked by `test_cancel_ends_cancelled`. `tests/unit/test_benchmark.py` `test_failed_stream_is_recorded_once` and `test_cancel_signal_records_each_started_attempt_once` lock `success` and `error_type` on the runner's rows. `test_progress_sink_receives_rows_and_samples_and_no_status` locks that the runner's progress items are request rows and samples, not those five names.
