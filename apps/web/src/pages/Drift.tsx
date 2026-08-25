import { api } from "../api";
import { usePoll } from "../usePoll";

export function Drift() {
  const { data } = usePoll(() => api.drift(), 4000, "drift-page");
  const byFeature = (data?.data_drift?.metrics?.by_feature ?? {}) as Record<string, number>;

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="kicker">Monitoring</p>
          <h1>Drift vs frozen reference</h1>
        </div>
        <p className={`status ${data?.status ?? "pending"}`}>{data?.status ?? "pending"}</p>
      </header>
      <p className="lede">{data?.note}</p>
      <div className="grid-3">
        <article className="panel">
          <h2>Data drift</h2>
          <p className="mono-lg">{fmtPsi(data?.data_drift?.psi)}</p>
          <p className="caption">Live features vs training feature distribution. PSI &gt; 0.20 enqueues retrain.</p>
        </article>
        <article className="panel">
          <h2>Prediction drift</h2>
          <p className="mono-lg">{fmtPsi(data?.prediction_drift?.psi)}</p>
          <p className="caption">Live scores vs active-model scores on the training reference population. Not proof of worse performance.</p>
        </article>
        <article className="panel">
          <h2>Model performance</h2>
          <p className="mono-lg delayed">delayed</p>
          <p className="caption">
            {(data?.performance?.metrics as { reason?: string } | undefined)?.reason ??
              "Labels need T+14d."}
          </p>
        </article>
      </div>
      <article className="panel">
        <h2>PSI by feature</h2>
        <table className="grid">
          <thead>
            <tr>
              <th>Feature</th>
              <th>PSI</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(byFeature)
              .sort((a, b) => b[1] - a[1])
              .map(([name, psi]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td className="num">{psi.toFixed(3)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}

function fmtPsi(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}
