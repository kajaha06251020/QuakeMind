"""LLM駆動の仮説自動生成。分析結果から科学的仮説を自然言語で生成する。"""
import logging
from datetime import datetime, timezone

from app.services.hypothesis_engine import create_hypothesis
from app.services.research_journal import add_entry

logger = logging.getLogger(__name__)


async def generate_hypotheses_from_analysis(analysis_results: dict) -> list[dict]:
    """分析結果から科学的仮説を自動生成する。ルールベース + テンプレート。"""
    hypotheses = []

    # b値低下 → 大地震前兆仮説
    b_change = analysis_results.get("b_value_change")
    if b_change is not None and b_change < -0.15:
        b_latest = analysis_results.get("b_value_latest", 0)
        h = {
            "title": f"b値低下({b_latest:.2f})は大地震の前兆である",
            "description": f"b値が{abs(b_change):.2f}低下。Bath則に基づき、応力集中による大地震（M5+）の発生確率が上昇している可能性。",
            "evidence": ["b_value_drop", f"change={b_change:.3f}"],
            "mechanism": "応力集中 → 小地震のb値低下 → 大地震核形成",
            "testable_prediction": "30日以内にM5以上が発生する",
            "verify_days": 30,
        }
        hypotheses.append(h)

    # クラスタ検出 → 群発地震進行仮説
    n_clusters = analysis_results.get("n_clusters", 0)
    if n_clusters >= 2:
        h = {
            "title": f"複数クラスタ({n_clusters}個)は流体移動による誘発地震",
            "description": f"{n_clusters}個のクラスタが検出。地殻内の流体移動が複数箇所で地震を誘発している可能性。",
            "evidence": ["multiple_clusters", f"n={n_clusters}"],
            "mechanism": "地殻流体の移動 → 間隙水圧上昇 → 有効応力低下 → 地震発生",
            "testable_prediction": "クラスタ間に時空間的な移動パターンがある",
            "verify_days": 14,
        }
        hypotheses.append(h)

    # 異常活動 → 活動活発化仮説
    anomaly = analysis_results.get("anomaly_detected", False)
    if anomaly:
        p_value = analysis_results.get("p_value", 1.0)
        h = {
            "title": "統計的に有意な活動活発化が進行中",
            "description": f"ポアソン検定でp={p_value:.4f}。背景発生率を有意に上回る活動。前震活動の可能性。",
            "evidence": ["anomaly_detection", f"p_value={p_value}"],
            "mechanism": "応力場の変化 → 発生率の増加 → 前震シーケンス",
            "testable_prediction": "7日以内にM4以上が発生する、または活動が収束する",
            "verify_days": 7,
        }
        hypotheses.append(h)

    # 静穏化 → 応力ロック仮説
    quiescence = analysis_results.get("is_quiescent", False)
    if quiescence:
        h = {
            "title": "静穏化は断層のロッキングを示唆",
            "description": "地震活動の有意な低下。断層面の固着（ロッキング）が進行し、応力が蓄積している可能性。",
            "evidence": ["quiescence_detected"],
            "mechanism": "断層ロッキング → 応力蓄積 → 静穏化 → 将来の大地震",
            "testable_prediction": "静穏化終了後にM5+が発生する",
            "verify_days": 60,
        }
        hypotheses.append(h)

    # カスケード確率高 → 連鎖地震仮説
    cascade_risk = analysis_results.get("highest_cascade_prob", 0)
    if cascade_risk > 0.01:
        h = {
            "title": "クーロン応力伝播による連鎖地震リスク",
            "description": f"隣接断層へのカスケード確率が{cascade_risk:.4f}。応力伝播による誘発地震の可能性。",
            "evidence": ["cascade_probability", f"prob={cascade_risk}"],
            "mechanism": "主震 → クーロン応力変化 → 隣接断層の促進 → 連鎖地震",
            "testable_prediction": "7日以内に隣接断層で地震が発生する",
            "verify_days": 7,
        }
        hypotheses.append(h)

    # デフォルト: 何も検出されない場合
    if not hypotheses:
        hypotheses.append({
            "title": "現在の地震活動は背景レベルで推移",
            "description": "特筆すべき異常パターンは検出されていない。通常のテクトニクス活動。",
            "evidence": ["no_anomaly"],
            "mechanism": "定常的なプレート運動による背景地震活動",
            "testable_prediction": "今後30日間はM6以上の発生なし",
            "verify_days": 30,
        })

    # 仮説をDBに登録
    registered = []
    for h in hypotheses:
        hyp_id = await create_hypothesis(
            title=h["title"], description=h["description"],
            trigger_event=str(h.get("evidence", [])),
            verify_after_days=h.get("verify_days", 30),
            evidence=h.get("evidence"),
        )
        h["hypothesis_id"] = hyp_id
        registered.append(h)

    await add_entry("finding", f"{len(registered)}個の仮説を自動生成",
        "\n".join(f"- {h['title']}" for h in registered),
        metadata={"n_hypotheses": len(registered)})

    return registered
