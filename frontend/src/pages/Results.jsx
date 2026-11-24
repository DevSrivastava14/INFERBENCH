import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SeriesChart } from "../components/SeriesChart.jsx";
import { ledes, resultMetrics } from "../copy.js";
import { loadExperiment } from "../services/experiments.js";

function metricValue(summary, key) {
  if (!summary || summary[key] === null || summary[key] === undefined || summary[key] === "") {
    return "unset";
  }
  return String(summary[key]);
}

export function Results() {
  const [params] = useSearchParams();
  const source = params.get("source");
  const id = params.get("id");
  const selected = Boolean(source && id);
  const [experiment, setExperiment] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!selected) {
      return undefined;
    }
    let active = true;
    setExperiment(null);
    setFailed(false);
    loadExperiment(source, id).then(
      (data) => {
        if (active) {
          setExperiment(data);
        }
      },
      () => {
        if (active) {
          setFailed(true);
        }
      },
    );
    return () => {
      active = false;
    };
  }, [selected, source, id]);

  const series =
    experiment && Array.isArray(experiment.measured)
      ? experiment.measured.map((row) => row.end_to_end_ms)
      : undefined;

  return (
    <>
      <p className="lede">{ledes.results}</p>
      <ul className="metric-list">
        {resultMetrics.map(([name, key, sentence]) => (
          <li key={name}>
            <span>{name}</span>
            <span className="caption">{sentence}</span>
            <span> {metricValue(experiment ? experiment.summary : null, key)}</span>
          </li>
        ))}
      </ul>
      {!selected ? <p className="empty">No experiment is selected.</p> : null}
      {failed ? <p className="empty">The load failed.</p> : null}
      <SeriesChart series={selected ? series : undefined} />
    </>
  );
}
