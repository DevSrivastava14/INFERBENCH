import { useEffect, useRef, useState } from "react";
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

function statusCell(value) {
  const text = cell(value);
  if (text === "") {
    return "";
  }
  return (
    <span className="status" data-status={text}>
      {text}
    </span>
  );
}

export function History() {
  const [rows, setRows] = useState(null);
  const [failed, setFailed] = useState(false);
  const railRef = useRef(null);
  const tableScrollRef = useRef(null);
  const scrollLock = useRef(false);

  function syncScroll(source, target) {
    if (!source || !target || scrollLock.current) {
      return;
    }
    if (source.scrollLeft === target.scrollLeft) {
      return;
    }
    scrollLock.current = true;
    target.scrollLeft = source.scrollLeft;
    requestAnimationFrame(() => {
      scrollLock.current = false;
    });
  }

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
          <td key={key} className={`col-${key}`}>
            {key === "id" ? (
              <Link to={`/results?source=${encodeURIComponent(row.source)}&id=${row.id}`}>
                {cell(row.id)}
              </Link>
            ) : key === "job_status" ? (
              statusCell(row.job_status)
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
      <div
        className="history-rail"
        ref={railRef}
        aria-label="History columns"
        onScroll={(event) => syncScroll(event.currentTarget, tableScrollRef.current)}
      >
        <div className="history-rail-inner" />
      </div>
      <div
        className="table-scroll history-scroll"
        ref={tableScrollRef}
        onScroll={(event) => syncScroll(event.currentTarget, railRef.current)}
      >
        <table className="data-table history-table">
          <colgroup>
            {columns.map(([key]) => (
              <col key={key} className={`col-${key}`} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {columns.map(([key, label]) => (
                <th key={label} scope="col" className={`col-${key}`}>
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
