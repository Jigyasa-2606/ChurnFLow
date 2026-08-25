import { api } from "../api";
import { usePoll } from "../usePoll";

export function Pipeline() {
  const { data: pipeline } = usePoll(() => api.pipeline(), 2500, "pipe-page");
  const { data: health } = usePoll(() => api.health(), 2500, "health");

  const p95 = pipeline?.p95_prediction_latency_ms;
  const slo = pipeline?.slo.api_predict_p95_ms ?? 1000;

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="kicker">Serving path</p>
          <h1>Pipeline health</h1>
        </div>
      </header>
      <div className="kpi-row">
        <article className="kpi">
          <span>API</span>
          <strong>{health == null ? "—" : health.ok ? "up" : "down"}</strong>
        </article>
        <article className="kpi">
          <span>Redis</span>
          <strong>{health == null ? "—" : health.redis ? "up" : "down"}</strong>
        </article>
        <article className="kpi">
          <span>Events ingested</span>
          <strong>{pipeline?.events?.toLocaleString() ?? "—"}</strong>
        </article>
        <article className="kpi">
          <span>Predictions (5m)</span>
          <strong>{pipeline?.predictions_last_5m ?? "—"}</strong>
        </article>
      </div>
      <article className="panel">
        <h2>Measured latency vs SLO</h2>
        <p className="mono-lg">{p95 === null || p95 === undefined ? "—" : `${p95.toFixed(2)} ms p95`}</p>
        <p className="caption">
          API predict SLO is {slo} ms. Full path event → prediction SLO is{" "}
          {pipeline?.slo.event_to_prediction_p95_ms ?? "—"} ms.
        </p>
        <p className="caption">Active model {pipeline?.active_model}</p>
        <p className="caption">Last event timestamp {pipeline?.last_event_ts ?? "—"}</p>
        <p className="caption">
          Infra Grafana (linked, not embedded):{" "}
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">
            localhost:3000
          </a>
        </p>
      </article>
    </section>
  );
}
