import { useState } from "react";

const profiles = [
  "short_prompt_short_output",
  "long_prompt_short_output",
  "short_prompt_long_output",
  "long_prompt_long_output",
];

export function Benchmark() {
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [profileName, setProfileName] = useState("");
  const [numPredict, setNumPredict] = useState("");
  const [warmupCount, setWarmupCount] = useState("");
  const [measuredCount, setMeasuredCount] = useState("");
  const [concurrency, setConcurrency] = useState("");
  const [think, setThink] = useState("");
  const [numThread, setNumThread] = useState("");

  return (
    <form className="form" onSubmit={(event) => event.preventDefault()}>
      <label>
        <span className="field-name">model</span>
        <input value={model} onChange={(event) => setModel(event.target.value)} />
      </label>
      <label>
        <span className="field-name">prompt</span>
        <textarea
          rows={4}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
      </label>
      <label>
        <span className="field-name">profile name</span>
        <select
          value={profileName}
          onChange={(event) => setProfileName(event.target.value)}
        >
          <option value=""></option>
          {profiles.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="field-name">num_predict</span>
        <input
          value={numPredict}
          onChange={(event) => setNumPredict(event.target.value)}
        />
      </label>
      <label>
        <span className="field-name">warm-up count</span>
        <input
          value={warmupCount}
          onChange={(event) => setWarmupCount(event.target.value)}
        />
      </label>
      <label>
        <span className="field-name">measured count</span>
        <input
          value={measuredCount}
          onChange={(event) => setMeasuredCount(event.target.value)}
        />
      </label>
      <label>
        <span className="field-name">concurrency</span>
        <input
          value={concurrency}
          onChange={(event) => setConcurrency(event.target.value)}
        />
      </label>
      <label>
        <span className="field-name">think</span>
        <select value={think} onChange={(event) => setThink(event.target.value)}>
          <option value="">omitted</option>
          <option value="false">false</option>
          <option value="true">true</option>
        </select>
      </label>
      <label>
        <span className="field-name">num_thread</span>
        <input
          value={numThread}
          onChange={(event) => setNumThread(event.target.value)}
        />
      </label>
      <p className="note">Streaming is the benchmark path the runner already uses.</p>
    </form>
  );
}
