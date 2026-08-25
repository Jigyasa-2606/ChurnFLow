import { Link } from "react-router-dom";
import { api } from "../api";
import { usePoll } from "../usePoll";

export function Risk() {
  const { data } = usePoll(() => api.customers(), 2500, "risk");
  const rows = data?.customers ?? [];
  return (
    <section>
      <header className="page-head">
        <div>
          <p className="kicker">Risk table</p>
          <h1>All scored customers</h1>
        </div>
      </header>
      <article className="panel">
        <table className="grid">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Score</th>
              <th>Risk</th>
              <th>Model</th>
              <th>Scored at</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.customer_id}>
                <td>
                  <Link to={`/customers/${row.customer_id}`}>{row.customer_id}</Link>
                </td>
                <td className="num">{row.score.toFixed(4)}</td>
                <td>
                  <span className={`pill ${row.risk.toLowerCase()}`}>{row.risk}</span>
                </td>
                <td className="mono">{row.model_version}</td>
                <td className="mono">{row.scored_at ? new Date(row.scored_at).toLocaleTimeString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}
