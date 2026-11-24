import { useEffect, useState } from "react";
import { jobRequestBody, loadJob, startJob } from "../services/experiments.js";

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
  const [job, setJob] = useState(null);
  const [failed, setFailed] = useState(false);

  const jobId = job ? job.id : null;
  const jobStatus = job ? job.job_status : null;

  useEffect(() => {
    if (!jobId || (jobStatus !== "PENDING" && jobStatus !== "RUNNING")) {
      return undefined;
    }
    let active = true;
    const timer = setInterval(() => {
      loadJob(jobId).then(
        (next) => {
          if (active) {
            setJob(next);
          }
        },
        () => {
          if (active) {
            setFailed(true);
          }
        },
      );
    }, 200);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [jobId, jobStatus]);

  function onSubmit(event) {
    event.preventDefault();
    setFailed(false);
    setJob(null);
    startJob(
      jobRequestBody({
        model,
        prompt,
        profileName,
        numPredict,
        warmupCount,
        measuredCount,
        concurrency,
        think,
        numThread,
      }),
    ).then(
      (created) => {
        setJob(created);
      },
      () => {
        setFailed(true);
      },
    );
  }

  const sample = job && job.latest_sample ? job.latest_sample : null;

  return (
    <form className="form" onSubmit={onSubmit}>
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
      <button type="submit">Run</button>
      {failed ? <p className="empty">The load failed.</p> : null}
      {job ? (
        <>
          <p className="note">{job.job_status}</p>
          {job.succeeded_count !== undefined && job.succeeded_count !== null ? (
            <p className="note">succeeded {job.succeeded_count}</p>
          ) : null}
          {job.failed_count !== undefined && job.failed_count !== null ? (
            <p className="note">failed {job.failed_count}</p>
          ) : null}
          {sample ? (
            <p className="note">
              cpu_percent {sample.cpu_percent} system_ram_used_bytes{" "}
              {sample.system_ram_used_bytes}
            </p>
          ) : null}
        </>
      ) : null}
    </form>
  );
}
