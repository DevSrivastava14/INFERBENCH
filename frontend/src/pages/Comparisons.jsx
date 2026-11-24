import { useState } from "react";
import { compareExperiments, compareRequestBody } from "../services/experiments.js";

const deltas = [
  "average_ms_delta",
  "median_ms_delta",
  "p50_ms_delta",
  "p95_ms_delta",
  "p99_ms_delta",
  "error_rate_delta",
  "generation_throughput_tps_delta",
  "request_throughput_rps_delta",
];

function display(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return String(value);
}

export function Comparisons() {
  const [baselineSource, setBaselineSource] = useState("");
  const [baselineId, setBaselineId] = useState("");
  const [candidateSource, setCandidateSource] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [result, setResult] = useState(null);
  const [failed, setFailed] = useState(false);

  function onSubmit(event) {
    event.preventDefault();
    setFailed(false);
    setResult(null);
    compareExperiments(
      compareRequestBody({
        baselineSource,
        baselineId,
        candidateSource,
        candidateId,
      }),
    ).then(
      (payload) => {
        setResult(payload);
      },
      () => {
        setFailed(true);
      },
    );
  }

  const differences = result ? result.setting_differences ?? [] : [];

  return (
    <>
      <form className="form" onSubmit={onSubmit}>
        <label>
          <span className="field-name">baseline source</span>
          <input
            value={baselineSource}
            onChange={(event) => setBaselineSource(event.target.value)}
          />
        </label>
        <label>
          <span className="field-name">baseline id</span>
          <input
            value={baselineId}
            onChange={(event) => setBaselineId(event.target.value)}
          />
        </label>
        <label>
          <span className="field-name">candidate source</span>
          <input
            value={candidateSource}
            onChange={(event) => setCandidateSource(event.target.value)}
          />
        </label>
        <label>
          <span className="field-name">candidate id</span>
          <input
            value={candidateId}
            onChange={(event) => setCandidateId(event.target.value)}
          />
        </label>
        <button type="submit">Compare</button>
      </form>
      {failed ? <p className="empty">The load failed.</p> : null}
      {!failed && !result ? <p className="empty">Nothing is loaded.</p> : null}
      {result ? (
        <div className="region-list">
          <section className="region">
            <h2>deltas</h2>
            <ul className="metric-list">
              {deltas.map((name) => (
                <li key={name}>
                  {name} {display(result[name])}
                </li>
              ))}
            </ul>
          </section>
          <section className="region">
            <h2>phase labels</h2>
            <ul className="metric-list">
              <li>baseline_phase_label {display(result.baseline_phase_label)}</li>
              <li>candidate_phase_label {display(result.candidate_phase_label)}</li>
            </ul>
          </section>
          <section className="region">
            <h2>setting differences</h2>
            {differences.length === 0 ? null : (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>field</th>
                      <th>baseline</th>
                      <th>candidate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {differences.map((item) => (
                      <tr key={item.field}>
                        <td>{display(item.field)}</td>
                        <td>{display(item.baseline)}</td>
                        <td>{display(item.candidate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          {typeof result.sign_sentence === "string" && result.sign_sentence !== "" ? (
            <p className="note">{result.sign_sentence}</p>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
