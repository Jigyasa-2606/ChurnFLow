import { useParams } from "react-router-dom";
import { api } from "../api";
import { usePoll } from "../usePoll";

export function Customer() {
  const { id = "" } = useParams();
  const { data, error } = usePoll(() => api.customer(id), 3000, id);

  const features = Object.entries(data?.features ?? {}).filter(([key]) => !key.startsWith("_"));

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="kicker">Customer</p>
          <h1>{id}</h1>
        </div>
      </header>
      {error ? <p className="error">{error}</p> : null}
      <div className="grid-2">
        <article className="panel">
          <h2>Latest score</h2>
          <p className="mono-lg">{data?.latest_score?.score ?? "—"}</p>
          <p className="caption">
            {data?.latest_score?.risk} · {data?.latest_score?.model_version}
          </p>
        </article>
        <article className="panel">
          <h2>Observation</h2>
          <p className="caption">Features at T = event time / scoring timestamp (`event.ts ≤ T`)</p>
          <p className="mono">{data?.features?._observation_time ?? "—"}</p>
          <p className="caption">features_version {data?.features?._features_version ?? "—"}</p>
        </article>
      </div>
      <article className="panel">
        <h2>Feature vector</h2>
        <table className="grid">
          <tbody>
            {features.map(([name, value]) => (
              <tr key={name}>
                <td>{name}</td>
                <td className="num">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
      <article className="panel">
        <h2>Score history</h2>
        <table className="grid">
          <thead>
            <tr>
              <th>Time</th>
              <th>Score</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            {(data?.history ?? []).slice(0, 12).map((row, idx) => (
              <tr key={`${row.scoring_ts}-${idx}`}>
                <td className="mono">{new Date(row.scoring_ts).toLocaleTimeString()}</td>
                <td className="num">{row.score.toFixed(4)}</td>
                <td className="num">{row.latency_ms?.toFixed(2)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}
