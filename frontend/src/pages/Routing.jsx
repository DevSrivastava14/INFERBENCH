import { useState } from "react";
import { ledes, routingFields, routingPolicies } from "../copy.js";
import { routeCall, routeRequestBody } from "../services/experiments.js";

const policies = [
  "static",
  "workload_aware",
  "latency_constrained",
  "availability_aware",
];

function display(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return String(value);
}

export function Routing() {
  const [policy, setPolicy] = useState("static");
  const [profileName, setProfileName] = useState("");
  const [staticModel, setStaticModel] = useState("");
  const [unavailable, setUnavailable] = useState("");
  const [catalogModel, setCatalogModel] = useState("");
  const [capabilities, setCapabilities] = useState("");
  const [modelSizeBytes, setModelSizeBytes] = useState("");
  const [averageMs, setAverageMs] = useState("");
  const [medianMs, setMedianMs] = useState("");
  const [p50Ms, setP50Ms] = useState("");
  const [p95Ms, setP95Ms] = useState("");
  const [p99Ms, setP99Ms] = useState("");
  const [requiredCapabilities, setRequiredCapabilities] = useState("");
  const [maxModelSizeBytes, setMaxModelSizeBytes] = useState("");
  const [budgetMetric, setBudgetMetric] = useState("");
  const [budgetMaximum, setBudgetMaximum] = useState("");
  const [decision, setDecision] = useState(null);
  const [failed, setFailed] = useState(false);

  function onSubmit(event) {
    event.preventDefault();
    setFailed(false);
    setDecision(null);
    routeCall(
      routeRequestBody({
        policy,
        profileName,
        staticModel,
        unavailable,
        catalogModel,
        capabilities,
        modelSizeBytes,
        average_ms: averageMs,
        median_ms: medianMs,
        p50_ms: p50Ms,
        p95_ms: p95Ms,
        p99_ms: p99Ms,
        requiredCapabilities,
        maxModelSizeBytes,
        budgetMetric,
        budgetMaximum,
      }),
    ).then(
      (payload) => {
        setDecision(payload);
      },
      () => {
        setFailed(true);
      },
    );
  }

  const failures = decision ? decision.failed_constraints ?? [] : [];

  return (
    <>
      <p className="lede">{ledes.routing}</p>
      <form className="form" onSubmit={onSubmit}>
        <Field name="policy" sentence={routingFields.policy}>
          <select value={policy} onChange={(event) => setPolicy(event.target.value)}>
            {policies.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </Field>
        {policies.map((name) => (
          <p className="caption" key={name}>
            {routingPolicies[name]}
          </p>
        ))}
        <Field name="profile name" sentence={routingFields["profile name"]}>
          <input
            value={profileName}
            onChange={(event) => setProfileName(event.target.value)}
          />
        </Field>
        <Field name="static model" sentence={routingFields["static model"]}>
          <input
            value={staticModel}
            onChange={(event) => setStaticModel(event.target.value)}
          />
        </Field>
        <Field name="unavailable" sentence={routingFields.unavailable}>
          <input
            value={unavailable}
            onChange={(event) => setUnavailable(event.target.value)}
          />
        </Field>
        <Field name="catalog model" sentence={routingFields["catalog model"]}>
          <input
            value={catalogModel}
            onChange={(event) => setCatalogModel(event.target.value)}
          />
        </Field>
        <Field name="capabilities" sentence={routingFields.capabilities}>
          <input
            value={capabilities}
            onChange={(event) => setCapabilities(event.target.value)}
          />
        </Field>
        <Field name="model_size_bytes" sentence={routingFields.model_size_bytes}>
          <input
            value={modelSizeBytes}
            onChange={(event) => setModelSizeBytes(event.target.value)}
          />
        </Field>
        <Field name="stored average_ms" sentence={routingFields["stored average_ms"]}>
          <input
            value={averageMs}
            onChange={(event) => setAverageMs(event.target.value)}
          />
        </Field>
        <Field name="stored median_ms" sentence={routingFields["stored median_ms"]}>
          <input
            value={medianMs}
            onChange={(event) => setMedianMs(event.target.value)}
          />
        </Field>
        <Field name="stored p50_ms" sentence={routingFields["stored p50_ms"]}>
          <input value={p50Ms} onChange={(event) => setP50Ms(event.target.value)} />
        </Field>
        <Field name="stored p95_ms" sentence={routingFields["stored p95_ms"]}>
          <input value={p95Ms} onChange={(event) => setP95Ms(event.target.value)} />
        </Field>
        <Field name="stored p99_ms" sentence={routingFields["stored p99_ms"]}>
          <input value={p99Ms} onChange={(event) => setP99Ms(event.target.value)} />
        </Field>
        <Field name="required capabilities" sentence={routingFields["required capabilities"]}>
          <input
            value={requiredCapabilities}
            onChange={(event) => setRequiredCapabilities(event.target.value)}
          />
        </Field>
        <Field name="max_model_size_bytes" sentence={routingFields.max_model_size_bytes}>
          <input
            value={maxModelSizeBytes}
            onChange={(event) => setMaxModelSizeBytes(event.target.value)}
          />
        </Field>
        <Field name="latency budget metric" sentence={routingFields["latency budget metric"]}>
          <input
            value={budgetMetric}
            onChange={(event) => setBudgetMetric(event.target.value)}
          />
        </Field>
        <Field name="latency budget maximum" sentence={routingFields["latency budget maximum"]}>
          <input
            value={budgetMaximum}
            onChange={(event) => setBudgetMaximum(event.target.value)}
          />
        </Field>
        <button type="submit">Route</button>
      </form>
      {failed ? <p className="empty">The load failed.</p> : null}
      {!failed && !decision ? <p className="empty">Nothing is loaded.</p> : null}
      {decision ? (
        <div className="region-list">
          <section className="region">
            <h2>decision</h2>
            <ul className="metric-list">
              <li>selected_model {display(decision.selected_model)}</li>
              <li>preferred_model {display(decision.preferred_model)}</li>
              <li>reason {display(decision.reason)}</li>
              <li>fallback_count {display(decision.fallback_count)}</li>
            </ul>
          </section>
          <section className="region">
            <h2>failed constraints</h2>
            {failures.length === 0 ? null : (
              <ul className="metric-list">
                {failures.map((item) => (
                  <li key={item}>{display(item)}</li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </>
  );
}

function Field({ name, sentence, children }) {
  return (
    <div>
      <label>
        <span className="field-name">{name}</span>
        {children}
      </label>
      <p className="caption">{sentence}</p>
    </div>
  );
}
