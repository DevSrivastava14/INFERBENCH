export const landingPurpose =
  "An engineering platform for measuring local LLM inference performance.";

export const ledes = {
  overview:
    "This page shows the engines, models, hardware, recent experiments, and the current CPU and RAM sample the API returned.",
  benchmark:
    "This page starts one benchmark job and shows its state while the run is in flight.",
  results:
    "This page shows the stored summary for one selected experiment. It does not calculate the metrics.",
  history:
    "This page lists stored experiments and the configuration saved with each one.",
  comparisons:
    "The delta is the candidate's stored aggregate minus the baseline's stored aggregate. This page does not rank one experiment above the other.",
  routing:
    "This page selects a model with one of four policies and shows the decision the router returned.",
};

export const overviewRegions = {
  "Inference engines": "Engines the API reported, including each version string.",
  Models: "Models the API reported.",
  Hardware: "The machine description the API returned.",
  "Recent experiments": "Experiments the API listed from stored files.",
  "Current CPU and RAM": "The latest CPU and memory sample. A failed load leaves this empty.",
};

export const benchmarkFields = {
  model: "The name of the model the run will call.",
  prompt: "The text sent on each call.",
  "profile name": "The workload profile stored with this run. Blank leaves it unset.",
  num_predict: "A cap on output tokens, not the number of tokens the model emitted.",
  "warm-up count": "Warm-up calls are stored and stay out of the measured set.",
  "measured count": "How many measured calls to run. Warm-up stays out of that set.",
  concurrency: "How many measured calls may be in flight at once.",
  think: "Omitted leaves the flag unset. False sends the flag as false.",
  num_thread: "A serving option. Blank stays unset and is not stored as zero.",
};

export const benchmarkControls = {
  streaming: "Streaming is the benchmark path the runner already uses.",
  run: "Run starts one job and returns before the model finishes.",
  cancel: "Cancel stops new calls and cancels calls already in flight.",
};

export const resultMetrics = [
  ["TTFT", "ttft_ms", "Time from the request start until the first generated content arrives. Unit: milliseconds."],
  ["TPOT", "tpot_ms", "Decode duration divided by output tokens minus one. Unit: milliseconds per token."],
  ["end-to-end latency", "average_ms", "Request completion time minus the request start time. Unit: milliseconds."],
  ["generation throughput", "generation_throughput_tps", "Output tokens divided by the client decode duration. Unit: tokens per second."],
  ["request throughput", "request_throughput_rps", "Completed measured requests divided by the measured window. Unit: requests per second."],
  ["P50", "p50_ms", "Nearest-rank middle of the successful measured end-to-end latencies. Unit: milliseconds."],
  ["P95", "p95_ms", "Nearest-rank latency that about 95 percent of successful measured requests were at or under. Unit: milliseconds."],
  ["P99", "p99_ms", "Nearest-rank latency that about 99 percent of successful measured requests were at or under. Unit: milliseconds."],
  ["error rate", "error_rate", "Failed measured requests divided by measured requests that were not cancelled. Unit: a fraction. A blank value is unset."],
];

export const historyCaptions = {
  source: "Which stored file this row came from.",
  id: "The id of the experiment inside that file.",
  model: "The model name stored on the snapshot.",
  "profile name": "The workload profile stored with the run. Blank means unset.",
  prompt: "The prompt stored on the snapshot.",
  num_predict: "The output cap stored on the snapshot, not the tokens the model emitted.",
  "warm-up count": "How many warm-up calls were configured. Warm-up stays out of the measured set.",
  "measured count": "How many measured calls were configured.",
  concurrency: "The measured-call cap stored on the snapshot.",
  think: "The think flag stored on the snapshot. Blank means it was omitted.",
  num_thread: "The thread value stored on the snapshot. Blank means it was omitted, not zero.",
  "job status": "The API job state. A blank cell means no job state was stored.",
};

export const comparisonFields = {
  "baseline source": "The stored file of the baseline experiment.",
  "baseline id": "The id of the baseline experiment in that file.",
  "candidate source": "The stored file of the candidate experiment.",
  "candidate id": "The id of the candidate experiment in that file.",
};

export const routingFields = {
  policy: "Which selection rule to apply.",
  "profile name": "The workload profile whose stored latency the policies read.",
  "static model": "The model name static selection returns.",
  unavailable: "Model names the availability-aware policy treats as unavailable.",
  "catalog model": "The one catalog row this form posts.",
  capabilities: "Capability labels copied onto that catalog row.",
  model_size_bytes: "The model file size copied onto that catalog row. Blank leaves it unset.",
  "stored average_ms": "A stored average the caller already has, in milliseconds. Blank leaves it unset.",
  "stored median_ms": "A stored median the caller already has, in milliseconds. Blank leaves it unset.",
  "stored p50_ms": "A stored P50 the caller already has, in milliseconds. Blank leaves it unset.",
  "stored p95_ms": "A stored P95 the caller already has, in milliseconds. Blank leaves it unset.",
  "stored p99_ms": "A stored P99 the caller already has, in milliseconds. Blank leaves it unset.",
  "required capabilities": "Capabilities a candidate must have. Blank filters nothing.",
  max_model_size_bytes: "The largest model file a candidate may have. Blank leaves size unfiltered.",
  "latency budget metric": "Which stored latency field the budget reads.",
  "latency budget maximum": "The budget limit for that field. Blank leaves the budget unset.",
};

export const routingPolicies = {
  static: "Static returns the configured model and keeps that name when a constraint fails.",
  workload_aware:
    "Workload-aware selection is the lowest stored P95 for the requested profile among models that pass the capability and size filters.",
  latency_constrained:
    "Latency-constrained adds the caller's latency budget as a further filter, then uses that same P95 rank.",
  availability_aware:
    "Availability-aware uses that P95 rank, then selects the next eligible model when the preferred model is unavailable.",
};
