"""Route Agent: 避難ルートを計算し、Claude で地域固有の注意事項を生成する。"""
import logging

from anthropic import AsyncAnthropic

from app.config import settings
from app.domain.models import EventState

logger = logging.getLogger(__name__)

_claude = AsyncAnthropic(
    api_key=settings.anthropic_api_key,
    max_retries=settings.claude_max_retries,
)

_FALLBACK_NOTES = "余震に注意してください。津波の恐れがある場合は高台に避難してください。最新の気象庁情報を確認してください。"


def _compute_danger_radius(magnitude: float) -> float:
    return min(max(10.0, magnitude * 15.0), 100.0)


def _estimate_safe_direction(latitude: float, longitude: float) -> str:
    ns = "南" if latitude > 36.5 else "北"
    ew = "西" if longitude > 137.5 else "東"
    return f"{ns}{ew}方向（内陸側）"


async def _generate_notes(
    region: str, magnitude: float, depth_km: float, tsunami_flag: bool
) -> tuple[str, bool]:
    tsunami_text = "あり" if tsunami_flag else "なし"
    prompt = (
        f"以下の地震情報をもとに、避難時の注意事項を3点以内で簡潔に述べてください。\n"
        f"- 地域: {region}\n- マグニチュード: {magnitude}\n"
        f"- 震源深度: {depth_km}km\n- 津波リスク: {tsunami_text}\n"
        f"箇条書きで、各項目50文字以内。"
    )
    try:
        response = await _claude.messages.create(
            model=settings.claude_model,
            max_tokens=300,
            system="あなたは防災情報アシスタントです。簡潔かつ正確に回答してください。",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip(), False
    except Exception as e:
        logger.warning("[Route] Claude 失敗、フォールバック: %s", e)
        return _FALLBACK_NOTES, True


async def route_node(state: EventState) -> dict:
    if state.get("error"):
        return {}
    try:
        danger_radius_km = _compute_danger_radius(state["magnitude"])
        safe_direction = _estimate_safe_direction(state["latitude"], state["longitude"])
        notes, is_fallback = await _generate_notes(
            state["region"], state["magnitude"], state["depth_km"],
            state.get("tsunami_flag", False),
        )
        logger.info("[Route] %s 半径=%.1fkm 方向=%s", state["event_id"], danger_radius_km, safe_direction)
        result = {"danger_radius_km": danger_radius_km, "safe_direction": safe_direction, "notes": notes}
        if is_fallback:
            result["is_fallback"] = True
        return result
    except Exception as e:
        logger.error("[Route] エラー: %s", e)
        return {"error": f"route: {e}"}
