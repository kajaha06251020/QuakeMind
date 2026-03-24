/**
 * FastAPI の Pydantic モデルを反映した TypeScript 型定義。
 * `npm run generate-api` (Orval) で自動生成に切り替え可能。
 */

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RiskScore {
  event_id: string;
  estimated_intensity: number;
  aftershock_prob_72h: number;
  tsunami_flag: boolean;
  severity: Severity;
  computed_at: string;
}

export interface AlertMessage {
  event_id: string;
  severity: Severity;
  ja_text: string;
  en_text: string;
  is_fallback: boolean;
  timestamp: string;
}

export interface StatusResponse {
  last_updated: string | null;
  data_stale: boolean;
  latest_risk_score: RiskScore | null;
  total_alerts: number;
}
