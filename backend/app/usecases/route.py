"""Route Agent: 避難ルートを計算し、LLMで地域固有の注意事項を生成する。"""
import logging

from app.domain.models import EventState
from app.usecases.llm_factory import generate_notes_with_fallback

logger = logging.getLogger(__name__)

_FALLBACK_NOTES = "余震に注意してください。津波の恐れがある場合は高台に避難してください。最新の気象庁情報を確認してください。"


def _compute_danger_radius(magnitude: float) -> float:
    return min(max(10.0, magnitude * 15.0), 100.0)


def _estimate_safe_direction(latitude: float, longitude: float) -> str:
    ns = "南" if latitude > 36.5 else "北"
    ew = "西" if longitude > 137.5 else "東"
    return f"{ns}{ew}方向（内陸側）"


async def route_node(state: EventState) -> dict:
    if state.get("error"):
        return {}
    try:
        danger_radius_km = _compute_danger_radius(state["magnitude"])
        safe_direction = _estimate_safe_direction(state["latitude"], state["longitude"])
        try:
            notes, is_fallback = await generate_notes_with_fallback(
                region=state["region"],
                magnitude=state["magnitude"],
                depth_km=state["depth_km"],
                tsunami_flag=state.get("tsunami_flag", False),
            )
        except Exception as e:
            logger.warning("[Route] LLM失敗、テンプレートフォールバック: %s", e)
            notes = _FALLBACK_NOTES
            is_fallback = True

        logger.info("[Route] %s 半径=%.1fkm 方向=%s", state["event_id"], danger_radius_km, safe_direction)
        result = {"danger_radius_km": danger_radius_km, "safe_direction": safe_direction, "notes": notes}
        if is_fallback:
            result["is_fallback"] = True
        return result
    except Exception as e:
        logger.error("[Route] エラー: %s", e)
        return {"error": f"route: {e}"}
