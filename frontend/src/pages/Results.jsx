import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SeriesChart } from "../components/SeriesChart.jsx";
import { loadExperiment } from "../services/experiments.js";

const metrics = [
  ["TTFT", "ttft_ms"],
  ["TPOT", "tpot_ms"],
  ["end-to-end latency", "average_ms"],
  ["generation throughput", "generation_throughput_tps"],
  ["request throughput", "request_throughput_rps"],
  ["P50", "p50_ms"],
  ["P95", "p95_ms"],
  ["P99", "p99_ms"],
  ["error rate", "error_rate"],
];

function metricValue(summary, key) {
  if (!summary || summary[key] === null || summary[key] === undefined) {
    return "";
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
      <ul className="metric-list">
        {metrics.map(([name, key]) => (
          <li key={name}>
            <span>{name}</span>
            {experiment ? <span> {metricValue(experiment.summary, key)}</span> : null}
          </li>
        ))}
      </ul>
      {!selected ? <p className="empty">No experiment is selected.</p> : null}
      {failed ? <p className="empty">The load failed.</p> : null}
      <SeriesChart series={selected ? series : undefined} />
    </>
  );
}
