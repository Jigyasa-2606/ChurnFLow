import { useState } from "react";
import { api } from "../api";
import { usePoll } from "../usePoll";

export function Models() {
  const { data } = usePoll(() => api.models(), 4000, "models");
  const [note, setNote] = useState<string | null>(null);

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="kicker">Registry</p>
          <h1>Model versions</h1>
        </div>
        <button
          className="btn"
          type="button"
          onClick={async () => {
            await api.retrain();
            setNote("Retrain queued. Promotion still requires AUC ≥ active + 0.01 and F1/logloss not worse.");
          }}
        >
          Queue retrain
        </button>
      </header>
      {note ? <p className="caption">{note}</p> : null}
      <p className="caption">Serving {data?.serving ?? "—"}</p>
      <article className="panel">
        <table className="grid">
          <thead>
            <tr>
              <th>Version</th>
              <th>Status</th>
              <th>AUC</th>
              <th>F1</th>
              <th>logloss</th>
              <th>Drift triggered</th>
            </tr>
          </thead>
          <tbody>
            {(data?.models ?? []).map((row) => (
              <tr key={row.model_version}>
                <td className="mono">{row.model_version}</td>
                <td>
                  <span className={`pill ${row.promotion_status}`}>{row.promotion_status}</span>
                </td>
                <td className="num">{row.auc?.toFixed(3)}</td>
                <td className="num">{row.f1?.toFixed(3)}</td>
                <td className="num">{row.logloss?.toFixed(3)}</td>
                <td>{row.drift_triggered ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}
