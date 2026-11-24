import { useEffect, useState } from "react";
import { loadOverview } from "../services/experiments.js";

const regions = [
  "Inference engines",
  "Models",
  "Hardware",
  "Recent experiments",
  "Current CPU and RAM",
];

function display(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return String(value);
}

export function Overview() {
  const [payload, setPayload] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    loadOverview().then(
      (data) => {
        if (active) {
          setPayload(data);
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
  }, []);

  if (failed) {
    return (
      <>
        <p className="empty">The load failed.</p>
        <div className="region-list">
          {regions.map((name) => (
            <section className="region" key={name}>
              <h2>{name}</h2>
            </section>
          ))}
        </div>
      </>
    );
  }

  return (
    <div className="region-list">
      {regions.map((name) => (
        <section className="region" key={name}>
          <h2>{name}</h2>
          <Region payload={payload} name={name} />
        </section>
      ))}
    </div>
  );
}

function Region({ payload, name }) {
  if (!payload) {
    return <p className="empty">Nothing is loaded.</p>;
  }
  if (name === "Inference engines") {
    const engines = payload.inference_engines ?? [];
    if (engines.length === 0) {
      return <p className="empty">Nothing is loaded.</p>;
    }
    return (
      <ul className="metric-list">
        {engines.map((engine) => (
          <li key={engine.name}>
            {display(engine.name)} {display(engine.version)}
          </li>
        ))}
      </ul>
    );
  }
  if (name === "Models") {
    const models = payload.models ?? [];
    if (models.length === 0) {
      return <p className="empty">Nothing is loaded.</p>;
    }
    return (
      <ul className="metric-list">
        {models.map((model) => (
          <li key={model.name}>{display(model.name)}</li>
        ))}
      </ul>
    );
  }
  if (name === "Hardware") {
    const hardware = payload.hardware;
    if (!hardware) {
      return <p className="empty">Nothing is loaded.</p>;
    }
    return (
      <ul className="metric-list">
        <li>cpu_model {display(hardware.cpu_model)}</li>
        <li>logical_cpu_count {display(hardware.logical_cpu_count)}</li>
        <li>total_ram_bytes {display(hardware.total_ram_bytes)}</li>
        <li>python_version {display(hardware.python_version)}</li>
      </ul>
    );
  }
  if (name === "Recent experiments") {
    const recent = payload.recent_experiments ?? [];
    if (recent.length === 0) {
      return <p className="empty">Nothing is loaded.</p>;
    }
    return (
      <ul className="metric-list">
        {recent.map((item) => (
          <li key={`${item.source}-${item.id}`}>
            {display(item.source)} {display(item.id)} {display(item.model)}
          </li>
        ))}
      </ul>
    );
  }
  const sample = payload.sample;
  if (!sample) {
    return <p className="empty">Nothing is loaded.</p>;
  }
  return (
    <ul className="metric-list">
      <li>cpu_percent {display(sample.cpu_percent)}</li>
      <li>system_ram_used_bytes {display(sample.system_ram_used_bytes)}</li>
      <li>system_ram_total_bytes {display(sample.system_ram_total_bytes)}</li>
    </ul>
  );
}
