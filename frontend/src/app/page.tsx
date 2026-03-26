import { api } from "@/lib/api-client";
import type { StatusResponse, AlertMessage, Severity } from "@/types/quakemind";

const SEVERITY_COLOR: Record<Severity, string> = {
  LOW: "#4ade80",
  MEDIUM: "#facc15",
  HIGH: "#fb923c",
  CRITICAL: "#f87171",
};

async function getPageData(): Promise<{
  status: StatusResponse | null;
  alert: AlertMessage | null;
}> {
  try {
    const [status, alert] = await Promise.allSettled([
      api.getStatus(),
      api.getLatestAlert(),
    ]);
    return {
      status: status.status === "fulfilled" ? status.value : null,
      alert: alert.status === "fulfilled" ? alert.value : null,
    };
  } catch {
    return { status: null, alert: null };
  }
}

export default async function DashboardPage() {
  const { status, alert } = await getPageData();

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>QuakeMind</h1>
      <p style={{ color: "#888", marginBottom: "2rem", fontSize: "0.875rem" }}>
        自律型防災 AGI — リアルタイム地震アラート
      </p>

      {/* システム状態 */}
      <section style={card}>
        <h2 style={sectionTitle}>システム状態</h2>
        {status ? (
          <dl style={dl}>
            <div style={row}>
              <dt style={dt}>最終更新</dt>
              <dd style={dd}>{status.last_updated ? new Date(status.last_updated).toLocaleString("ja-JP") : "—"}</dd>
            </div>
            <div style={row}>
              <dt style={dt}>データ鮮度</dt>
              <dd style={{ ...dd, color: status.data_stale ? "#f87171" : "#4ade80" }}>
                {status.data_stale ? "遅延あり" : "正常"}
              </dd>
            </div>
            <div style={row}>
              <dt style={dt}>累計アラート数</dt>
              <dd style={dd}>{status.total_alerts}</dd>
            </div>
          </dl>
        ) : (
          <p style={{ color: "#888" }}>バックエンドに接続できません</p>
        )}
      </section>

      {/* 最新アラート */}
      <section style={card}>
        <h2 style={sectionTitle}>最新アラート</h2>
        {alert ? (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <span
                style={{
                  background: SEVERITY_COLOR[alert.severity],
                  color: "#000",
                  padding: "0.2rem 0.6rem",
                  borderRadius: 4,
                  fontWeight: 700,
                  fontSize: "0.8rem",
                }}
              >
                {alert.severity}
              </span>
              <span style={{ color: "#888", fontSize: "0.8rem" }}>
                {new Date(alert.timestamp).toLocaleString("ja-JP")}
              </span>
              {alert.is_fallback && (
                <span style={{ color: "#888", fontSize: "0.75rem" }}>[フォールバック]</span>
              )}
            </div>
            <p style={{ lineHeight: 1.7, marginBottom: "0.75rem" }}>{alert.ja_text}</p>
            <p style={{ lineHeight: 1.7, color: "#aaa", fontSize: "0.875rem" }}>{alert.en_text}</p>
          </>
        ) : (
          <p style={{ color: "#888" }}>アラートはまだありません</p>
        )}
      </section>

      {/* 最新リスクスコア */}
      {status?.latest_risk_score && (
        <section style={card}>
          <h2 style={sectionTitle}>最新リスクスコア</h2>
          <dl style={dl}>
            <div style={row}>
              <dt style={dt}>推定震度</dt>
              <dd style={dd}>{status.latest_risk_score.estimated_intensity.toFixed(1)}</dd>
            </div>
            <div style={row}>
              <dt style={dt}>72h余震確率</dt>
              <dd style={dd}>{(status.latest_risk_score.aftershock_prob_72h * 100).toFixed(1)}%</dd>
            </div>
            <div style={row}>
              <dt style={dt}>津波リスク</dt>
              <dd style={{ ...dd, color: status.latest_risk_score.tsunami_flag ? "#f87171" : "#4ade80" }}>
                {status.latest_risk_score.tsunami_flag ? "あり" : "なし"}
              </dd>
            </div>
          </dl>
        </section>
      )}
    </main>
  );
}

// ─── スタイル定数 ──────────────────────────────────────────────────────────────
const card: React.CSSProperties = {
  background: "#1a1a1a",
  border: "1px solid #2a2a2a",
  borderRadius: 8,
  padding: "1.25rem",
  marginBottom: "1rem",
};
const sectionTitle: React.CSSProperties = { fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", marginTop: 0 };
const dl: React.CSSProperties = { margin: 0 };
const row: React.CSSProperties = { display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid #2a2a2a" };
const dt: React.CSSProperties = { color: "#888", fontSize: "0.875rem" };
const dd: React.CSSProperties = { margin: 0, fontSize: "0.875rem" };
