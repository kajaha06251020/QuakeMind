"""地震研究レポート生成。ローカルLLMを使用。"""
import logging
from datetime import datetime, timezone

from app.domain.seismology import EarthquakeRecord
from app.usecases.seismic_analysis import analyze_gutenberg_richter
from app.infrastructure.local_llm_provider import LocalLLMProvider
from app.infrastructure.claude_provider import ClaudeProvider
from app.config import settings
from app.domain.llm_provider import LLMError

logger = logging.getLogger(__name__)


async def generate_research_report(events: list[EarthquakeRecord]) -> dict:
    """地震イベントリストから研究レポートを生成する。"""
    if len(events) < 5:
        return {"error": "イベント数が不足しています（最低5件必要）"}

    # 統計情報を集める
    magnitudes = [e.magnitude for e in events]
    max_mag = max(magnitudes)
    min_mag = min(magnitudes)
    avg_mag = sum(magnitudes) / len(magnitudes)

    # GR解析（可能なら）
    gr_info = ""
    if len(events) >= 10:
        try:
            gr = analyze_gutenberg_richter(events)
            gr_info = f"b値: {gr.b_value:.2f} (Mc={gr.mc:.1f}, a値={gr.a_value:.2f})"
        except Exception:
            gr_info = "GR解析: データ不足"

    notes = ""
    try:
        if settings.llm_provider == "local":
            provider = LocalLLMProvider(settings.local_llm_base_url, settings.local_llm_timeout)
        else:
            provider = ClaudeProvider()
        notes = await provider.generate_notes("研究レポート", max_mag, 0, False)
    except Exception:
        notes = ""

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "magnitude_range": {"min": round(min_mag, 1), "max": round(max_mag, 1), "mean": round(avg_mag, 1)},
        "gr_analysis": gr_info,
        "report_text": notes if notes else "LLMが利用できないため、テキストレポートを生成できません。統計データは上記を参照してください。",
    }
