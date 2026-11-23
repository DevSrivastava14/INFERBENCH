import { SeriesChart } from "../components/SeriesChart.jsx";

const metrics = [
  "TTFT",
  "TPOT",
  "end-to-end latency",
  "generation throughput",
  "request throughput",
  "P50",
  "P95",
  "P99",
  "error rate",
];

export function Results() {
  return (
    <>
      <ul className="metric-list">
        {metrics.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
      <p className="empty">No experiment is selected.</p>
      <SeriesChart />
    </>
  );
}
