async function readJson(response) {
  if (!response.ok) {
    throw new Error("The load failed.");
  }
  return response.json();
}

export function loadExperiments() {
  return fetch("/api/history").then(readJson);
}

export function loadOverview() {
  return fetch("/api/overview").then(readJson);
}

export function loadExperiment(source, id) {
  return fetch(
    `/api/experiments/${encodeURIComponent(source)}/${encodeURIComponent(id)}`,
  ).then(readJson);
}

export function startJob(body) {
  return fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(readJson);
}

export function loadJob(id) {
  return fetch(`/api/jobs/${encodeURIComponent(id)}`).then(readJson);
}

export function cancelJob(id) {
  return fetch(`/api/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }).then(readJson);
}

export function compareExperiments(body) {
  return fetch("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(readJson);
}

export function routeCall(body) {
  return fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(readJson);
}

function optionalNumber(value) {
  const text = String(value).trim();
  if (text === "") {
    return undefined;
  }
  const number = Number(text);
  if (!Number.isFinite(number)) {
    return undefined;
  }
  return number;
}

export function jobRequestBody(fields) {
  const body = {
    model: fields.model,
    prompt: fields.prompt,
  };
  if (fields.profileName.trim() !== "") {
    body.profile_name = fields.profileName;
  }
  const numPredict = optionalNumber(fields.numPredict);
  if (numPredict !== undefined) {
    body.num_predict = numPredict;
  }
  const warmupCount = optionalNumber(fields.warmupCount);
  if (warmupCount !== undefined) {
    body.warmup_count = warmupCount;
  }
  const measuredCount = optionalNumber(fields.measuredCount);
  if (measuredCount !== undefined) {
    body.measured_count = measuredCount;
  }
  const concurrency = optionalNumber(fields.concurrency);
  if (concurrency !== undefined) {
    body.concurrency = concurrency;
  }
  const numThread = optionalNumber(fields.numThread);
  if (numThread !== undefined) {
    body.num_thread = numThread;
  }
  if (fields.model === "qwen3.5:2b") {
    body.think = false;
  } else if (fields.model !== "gemma3:1b" && fields.think === "false") {
    body.think = false;
  }
  return body;
}

export function compareRequestBody(fields) {
  return {
    baseline: {
      source: fields.baselineSource.trim(),
      id: Number(fields.baselineId),
    },
    candidate: {
      source: fields.candidateSource.trim(),
      id: Number(fields.candidateId),
    },
  };
}

function splitList(value) {
  return String(value)
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

export function routeRequestBody(fields) {
  const measurement = {};
  for (const key of ["average_ms", "median_ms", "p50_ms", "p95_ms", "p99_ms"]) {
    const number = optionalNumber(fields[key]);
    if (number !== undefined) {
      measurement[key] = number;
    }
  }
  const profileName = fields.profileName.trim();
  const catalogModel = fields.catalogModel.trim();
  const entry = {
    model: catalogModel,
    capabilities: splitList(fields.capabilities),
  };
  const modelSize = optionalNumber(fields.modelSizeBytes);
  if (modelSize !== undefined) {
    entry.model_size_bytes = modelSize;
  }
  if (profileName !== "" && Object.keys(measurement).length > 0) {
    entry.measurements = { [profileName]: measurement };
  }
  const request = {
    profile_name: profileName,
    required_capabilities: splitList(fields.requiredCapabilities),
  };
  const maxModelSize = optionalNumber(fields.maxModelSizeBytes);
  if (maxModelSize !== undefined) {
    request.max_model_size_bytes = maxModelSize;
  }
  const budgetMaximum = optionalNumber(fields.budgetMaximum);
  const budgetMetric = fields.budgetMetric.trim();
  if (budgetMetric !== "" && budgetMaximum !== undefined) {
    request.latency_budget = { metric: budgetMetric, maximum: budgetMaximum };
  }
  const staticModel = fields.staticModel.trim();
  if (staticModel !== "") {
    request.static_model = staticModel;
  }
  return {
    policy: fields.policy,
    catalog: catalogModel === "" ? [] : [entry],
    request,
    unavailable: splitList(fields.unavailable),
  };
}
