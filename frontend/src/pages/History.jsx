import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { historyCaptions, ledes } from "../copy.js";
import { loadExperiments } from "../services/experiments.js";

const columns = [
  ["source", "source"],
  ["id", "id"],
  ["model", "model"],
  ["profile_name", "profile name"],
  ["prompt", "prompt"],
  ["num_predict", "num_predict"],
  ["warmup_count", "warm-up count"],
  ["measured_count", "measured count"],
  ["concurrency", "concurrency"],
  ["think", "think"],
  ["num_thread", "num_thread"],
  ["job_status", "job status"],
];

function cell(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (value === false) {
    return "false";
  }
  if (value === true) {
    return "true";
  }
  return String(value);
}

export function History() {
  const [rows, setRows] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    loadExperiments().then(
      (data) => {
        if (active) {
          setRows(data);
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

  let body;
  if (failed) {
    body = (
      <tr>
        <td className="empty" colSpan={columns.length}>
          The load failed.
        </td>
      </tr>
    );
  } else if (!rows || rows.length === 0) {
    body = (
      <tr>
        <td className="empty" colSpan={columns.length}>
          Nothing is loaded.
        </td>
      </tr>
    );
  } else {
    body = rows.map((row) => (
      <tr key={`${row.source}-${row.id}`}>
        {columns.map(([key]) => (
          <td key={key}>
            {key === "id" ? (
              <Link to={`/results?source=${encodeURIComponent(row.source)}&id=${row.id}`}>
                {cell(row.id)}
              </Link>
            ) : (
              cell(row[key])
            )}
          </td>
        ))}
      </tr>
    ));
  }

  return (
    <>
      <p className="lede">{ledes.history}</p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map(([, label]) => (
                <th key={label} scope="col">
                  <span className="field-name">{label}</span>
                  <span className="caption">{historyCaptions[label]}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    </>
  );
}
