const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`);
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type CustomerRow = {
  customer_id: string;
  score: number;
  risk: string;
  model_version?: string;
  scored_at?: string;
  latency_ms?: number | null;
};

export type Pipeline = {
  active_model: string;
  events: number;
  last_event_ts: string | null;
  p95_prediction_latency_ms: number | null;
  predictions_last_5m: number;
  slo: { event_to_prediction_p95_ms: number; api_predict_p95_ms: number };
};

export type DriftPayload = {
  psi: number | null;
  metrics: Record<string, unknown>;
  reference_id: string;
  created_at: string | null;
};

export type DriftLatest = {
  status: string;
  threshold: number;
  data_drift: DriftPayload | null;
  prediction_drift: DriftPayload | null;
  performance: DriftPayload | null;
  note: string;
};

export type ModelRow = {
  model_version: string;
  training_time: string;
  features_version: string;
  auc: number;
  f1: number;
  logloss: number;
  drift_triggered: boolean;
  promotion_status: string;
};

export type CustomerDetail = {
  customer_id: string;
  features: Record<string, string>;
  latest_score: Record<string, string>;
  history: Array<{ score: number; model_version: string; scoring_ts: string; latency_ms: number }>;
};

export const api = {
  health: () => get<{ ok: boolean; model_version: string; redis: boolean }>("/health"),
  customers: (risk?: string) =>
    get<{ customers: CustomerRow[]; count: number }>(risk ? `/customers?risk=${risk}` : "/customers"),
  customer: (id: string) => get<CustomerDetail>(`/customers/${id}`),
  pipeline: () => get<Pipeline>("/pipeline"),
  drift: () => get<DriftLatest>("/drift/latest"),
  models: () => get<{ models: ModelRow[]; serving: string }>("/models"),
  retrain: () => fetch(`${API}/models/retrain`, { method: "POST" }).then((r) => r.json()),
};
