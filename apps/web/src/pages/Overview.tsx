import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type CustomerRow, type DriftLatest, type ModelRow, type Pipeline } from "../api";
import { usePoll } from "../usePoll";

function fmt(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function buckets(rows: CustomerRow[]): { label: string; count: number }[] {
  const edges = [0, 0.2, 0.4, 0.6, 0.8, 1.01];
  const labels = ["0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0"];
  const counts = [0, 0, 0, 0, 0];
  for (const row of rows) {
    for (let i = 0; i < 5; i += 1) {
      if (row.score >= edges[i] && row.score < edges[i + 1]) {
        counts[i] += 1;
        break;
      }
    }
  }
  return labels.map((label, i) => ({ label, count: counts[i] }));
}

export function Overview() {
  const { data: customers } = usePoll(() => api.customers(), 2500, "cust");
  const { data: pipeline } = usePoll(() => api.pipeline(), 2500, "pipe");
  const { data: drift } = usePoll(() => api.drift(), 4000, "drift");
  const { data: models } = usePoll(() => api.models(), 8000, "models");
  const eventsPerSec = useEventsPerSec(pipeline);

  const rows = customers?.customers ?? [];
  const high = rows.filter((row) => row.risk === "HIGH");
  const dist = buckets(rows);
  const maxBucket = Math.max(1, ...dist.map((d) => d.count));
  const active = models?.models.find((m) => m.promotion_status === "active");
  const p95 = pipeline?.p95_prediction_latency_ms ?? null;

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="kicker">ML Ops overview</p>
          <h1>Live churn risk</h1>
        </div>
        <p className="live-tag">polling 2.5s</p>
      </header>

      <div className="kpi-row">
        <Kpi label="Customers scored" value={fmt(rows.length)} />
        <Kpi label="High risk" value={fmt(high.length)} tone="warn" />
        <Kpi label="Events / sec" value={fmt(eventsPerSec, 1)} />
        <Kpi label="Predict p95" value={p95 === null ? "—" : `${fmt(p95, 1)} ms`} hint="measured, not a slogan" />
      </div>

      <div className="grid-2">
        <article className="panel">
          <h2>Churn risk distribution</h2>
          <p className="caption">Scores from the active model on live Redis features</p>
          <div className="bars">
            {dist.map((bucket) => (
              <div key={bucket.label} className="bar-row">
                <span>{bucket.label}</span>
                <div className="bar-track">
                  <div
                    className={`bar-fill${bucket.label.startsWith("0.8") ? " hot" : ""}`}
                    style={{ width: `${(bucket.count / maxBucket) * 100}%` }}
                  />
                </div>
                <em>{bucket.count}</em>
              </div>
            ))}
          </div>
        </article>

        <div className="stack">
          <DriftCard drift={drift} />
          <ActiveModelCard model={active} serving={models?.serving} />
        </div>
      </div>

      <article className="panel">
        <h2>Live high-risk customers</h2>
        <p className="caption">Score ≥ 0.70 · click through for the feature vector</p>
        <table className="grid">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Score</th>
              <th>Risk</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            {high.slice(0, 8).map((row) => (
              <tr key={row.customer_id}>
                <td>
                  <Link to={`/customers/${row.customer_id}`}>{row.customer_id}</Link>
                </td>
                <td className="num">{row.score.toFixed(3)}</td>
                <td>
                  <span className="pill high">HIGH</span>
                </td>
                <td className="num">{row.latency_ms ? `${row.latency_ms.toFixed(2)} ms` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}

function Kpi({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "warn";
}) {
  return (
    <article className={`kpi${tone === "warn" ? " warn" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint ? <small>{hint}</small> : null}
    </article>
  );
}

function DriftCard({ drift }: { drift: DriftLatest | null }) {
  const status = drift?.status ?? "pending";
  const psi = drift?.data_drift?.psi;
  return (
    <article className="panel compact">
      <h2>Drift status</h2>
      <p className={`status ${status}`}>{status}</p>
      <dl className="meta">
        <div>
          <dt>Data PSI</dt>
          <dd>{psi === null || psi === undefined ? "—" : psi.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Threshold</dt>
          <dd>0.20</dd>
        </div>
      </dl>
      <p className="caption">
        Prediction drift is logged separately. Performance waits on 14-day labels.
      </p>
    </article>
  );
}

function ActiveModelCard({ model, serving }: { model?: ModelRow; serving?: string }) {
  return (
    <article className="panel compact">
      <h2>Active model</h2>
      <p className="mono-lg">{serving ?? "—"}</p>
      <dl className="meta">
        <div>
          <dt>AUC</dt>
          <dd>{model ? model.auc.toFixed(3) : "—"}</dd>
        </div>
        <div>
          <dt>F1</dt>
          <dd>{model ? model.f1.toFixed(3) : "—"}</dd>
        </div>
        <div>
          <dt>logloss</dt>
          <dd>{model ? model.logloss.toFixed(3) : "—"}</dd>
        </div>
      </dl>
    </article>
  );
}

function useEventsPerSec(pipeline: Pipeline | null): number | null {
  const prev = useRef<{ events: number; t: number } | null>(null);
  const [rate, setRate] = useState<number | null>(null);
  useEffect(() => {
    if (!pipeline) return;
    const now = Date.now();
    if (prev.current) {
      const dt = (now - prev.current.t) / 1000;
      if (dt > 0.5) setRate((pipeline.events - prev.current.events) / dt);
    }
    prev.current = { events: pipeline.events, t: now };
  }, [pipeline]);
  return rate;
}
