import { loadExperiments } from "../services/experiments.js";

const columns = [
  "model",
  "profile name",
  "prompt",
  "num_predict",
  "warm-up count",
  "measured count",
  "concurrency",
  "think",
  "num_thread",
];

export function History() {
  const experiments = loadExperiments();

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {experiments.length === 0 ? (
            <tr>
              <td className="empty" colSpan={columns.length}>
                Nothing is loaded.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
