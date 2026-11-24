import { useEffect, useState } from "react";
import { benchmarkControls, benchmarkFields, ledes } from "../copy.js";
import { cancelJob, jobRequestBody, loadJob, startJob } from "../services/experiments.js";

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

  function onCancel() {
    if (!jobId) {
      return;
    }
    cancelJob(jobId).then(
      (next) => {
        setJob(next);
      },
      () => {
        setFailed(true);
      },
    );
  }

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

  const canCancel = jobStatus === "PENDING" || jobStatus === "RUNNING";

  return (
    <form className="form" onSubmit={onSubmit}>
      <p className="lede">{ledes.benchmark}</p>
      <Field name="model" sentence={benchmarkFields.model}>
        <input value={model} onChange={(event) => setModel(event.target.value)} />
      </Field>
      <Field name="prompt" sentence={benchmarkFields.prompt}>
        <textarea
          rows={4}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
      </Field>
      <Field name="profile name" sentence={benchmarkFields["profile name"]}>
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
      </Field>
      <Field name="num_predict" sentence={benchmarkFields.num_predict}>
        <input
          value={numPredict}
          onChange={(event) => setNumPredict(event.target.value)}
        />
      </Field>
      <Field name="warm-up count" sentence={benchmarkFields["warm-up count"]}>
        <input
          value={warmupCount}
          onChange={(event) => setWarmupCount(event.target.value)}
        />
      </Field>
      <Field name="measured count" sentence={benchmarkFields["measured count"]}>
        <input
          value={measuredCount}
          onChange={(event) => setMeasuredCount(event.target.value)}
        />
      </Field>
      <Field name="concurrency" sentence={benchmarkFields.concurrency}>
        <input
          value={concurrency}
          onChange={(event) => setConcurrency(event.target.value)}
        />
      </Field>
      <Field name="think" sentence={benchmarkFields.think}>
        <select value={think} onChange={(event) => setThink(event.target.value)}>
          <option value="">omitted</option>
          <option value="false">false</option>
        </select>
      </Field>
      <Field name="num_thread" sentence={benchmarkFields.num_thread}>
        <input
          value={numThread}
          onChange={(event) => setNumThread(event.target.value)}
        />
      </Field>
      <p className="note">{benchmarkControls.streaming}</p>
      <button type="submit">Run</button>
      <p className="caption">{benchmarkControls.run}</p>
      <button type="button" onClick={onCancel} disabled={!canCancel}>
        Cancel
      </button>
      <p className="caption">{benchmarkControls.cancel}</p>
      {failed ? <p className="empty">The load failed.</p> : null}
      {job ? (
        <>
          <p className="status" data-status={job.job_status}>
            {job.job_status}
          </p>
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
