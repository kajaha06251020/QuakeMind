"""Route Agent: 避難ルートを計算し、Claude で地域固有の注意事項を生成する。"""
import json
import logging
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from config import settings
from state import EventState

logger = logging.getLogger(__name__)

_claude = AsyncAnthropic(
    api_key=settings.anthropic_api_key,
    max_retries=settings.claude_max_retries,
)

# Claude 障害時のフォールバックテンプレート
_FALLBACK_NOTES = "余震に注意してください。津波の恐れがある場合は高台に避難してください。最新の気象庁情報を確認してください。"


def _compute_danger_radius(magnitude: float) -> float:
    """危険半径（km）。上限 100km。"""
    return min(max(10.0, magnitude * 15.0), 100.0)


def _estimate_safe_direction(latitude: float, longitude: float) -> str:
    """震源から見て内陸方向（簡易）。日本の地形を考慮した大まかな方向。"""
    # 日本の大まかな中心 (36.5N, 137.5E) を基準に震源の位置を判定
    if latitude > 36.5:
        ns = "南"
    else:
        ns = "北"
    if longitude > 137.5:
        ew = "西"
    else:
        ew = "東"
    return f"{ns}{ew}方向（内陸側）"


async def _generate_notes_with_claude(
    region: str,
    magnitude: float,
    depth_km: float,
    tsunami_flag: bool,
) -> tuple[str, bool]:
    """Claude で地域固有の避難注意事項を生成する。失敗時はフォールバックを返す。"""
    tsunami_text = "あり" if tsunami_flag else "なし"
    prompt = (
        f"以下の地震情報をもとに、避難時の注意事項を3点以内で簡潔に述べてください。\n"
        f"- 地域: {region}\n"
        f"- マグニチュード: {magnitude}\n"
        f"- 震源深度: {depth_km}km\n"
        f"- 津波リスク: {tsunami_text}\n"
        f"箇条書きで、各項目50文字以内。"
    )
    try:
        response = await _claude.messages.create(
            model=settings.claude_model,
            max_tokens=300,
            system="あなたは防災情報アシスタントです。簡潔かつ正確に回答してください。",
            messages=[{"role": "user", "content": prompt}],
        )
        notes = response.content[0].text.strip()
        return notes, False
    except Exception as e:
        logger.warning("[Route] Claude 呼び出し失敗、フォールバック使用: %s", e)
        return _FALLBACK_NOTES, True


async def route_node(state: EventState) -> dict:
    """LangGraph ノード: 避難ルートを計算して state を更新する。"""
    if state.get("error"):
        return {}

    try:
        magnitude = state["magnitude"]
        depth_km = state["depth_km"]
        tsunami_flag = state.get("tsunami_flag", False)

        danger_radius_km = _compute_danger_radius(magnitude)
        safe_direction = _estimate_safe_direction(state["latitude"], state["longitude"])
        notes, is_fallback = await _generate_notes_with_claude(
            state["region"], magnitude, depth_km, tsunami_flag
        )

        logger.info(
            "[Route] %s 危険半径=%.1fkm 方向=%s",
            state["event_id"], danger_radius_km, safe_direction,
        )

        result = {
            "danger_radius_km": danger_radius_km,
            "safe_direction": safe_direction,
            "notes": notes,
        }
        # フォールバックが発生した場合は is_fallback フラグを立てる（Personal に引き継ぐ）
        if is_fallback:
            result["is_fallback"] = True
        return result

    except Exception as e:
        logger.error("[Route] エラー: %s", e)
        return {"error": f"route: {e}"}
