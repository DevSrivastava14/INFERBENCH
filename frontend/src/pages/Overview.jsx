import { loadExperiments } from "../services/experiments.js";

const regions = [
  "Inference engines",
  "Models",
  "Hardware",
  "Recent experiments",
  "Current CPU and RAM",
];

export function Overview() {
  const experiments = loadExperiments();

  return (
    <div className="region-list">
      {regions.map((name) => (
        <section className="region" key={name}>
          <h2>{name}</h2>
          {name === "Recent experiments" && experiments.length > 0 ? null : (
            <p className="empty">Nothing is loaded.</p>
          )}
        </section>
      ))}
    </div>
  );
}
