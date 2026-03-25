"""Personal Agent: Claude でエンドユーザー向けアラート文を生成する。"""
import json
import logging
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from app.config import settings
from app.domain.models import EventState, AlertMessage, RiskScore, EvacuationRoute
from app.infrastructure import db

logger = logging.getLogger(__name__)

_claude = AsyncAnthropic(
    api_key=settings.anthropic_api_key,
    max_retries=settings.claude_max_retries,
)


def _fallback_texts(state: EventState) -> tuple[str, str]:
    ja = (
        f"{state['region']}でM{state['magnitude']}の地震が発生しました"
        f"（深度{state['depth_km']}km）。"
        f"深刻度: {state.get('severity', '不明')}。安全な場所に避難してください。"
    )
    en = (
        f"Earthquake M{state['magnitude']} near {state['region']} "
        f"(depth {state['depth_km']}km). "
        f"Severity: {state.get('severity', 'UNKNOWN')}. "
        f"Please evacuate to a safe location."
    )
    return ja, en


async def _generate_alert(state: EventState) -> tuple[str, str, bool]:
    prompt = (
        f"以下の情報からJSON形式で避難アラートを生成してください。\n"
        f"- 地域: {state['region']}, M{state['magnitude']}, 深度{state['depth_km']}km\n"
        f"- 深刻度: {state.get('severity', 'MEDIUM')}\n"
        f"- 推奨避難方向: {state.get('safe_direction', '安全な場所')}\n"
        f"- 注意事項: {state.get('notes', '')}\n\n"
        f'出力形式（JSONのみ）:\n'
        f'{{"ja_text": "（日本語、200文字以内）", "en_text": "（English, 150 chars max）"}}'
    )
    try:
        response = await _claude.messages.create(
            model=settings.claude_model,
            max_tokens=400,
            system="You are a concise emergency alert system. Output valid JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
        return data["ja_text"], data["en_text"], False
    except Exception as e:
        logger.warning("[Personal] Claude 失敗、フォールバック: %s", e)
        ja, en = _fallback_texts(state)
        return ja, en, True


async def personal_node(state: EventState) -> dict:
    if state.get("error"):
        logger.error("[Personal] 上流エラーのためスキップ: %s", state["error"])
        return {}
    try:
        ja_text, en_text, is_llm_fallback = await _generate_alert(state)
        is_fallback = is_llm_fallback or state.get("is_fallback", False)
        now = datetime.now(timezone.utc)
        severity = state.get("severity", "MEDIUM")

        alert = AlertMessage(
            event_id=state["event_id"], severity=severity,
            ja_text=ja_text, en_text=en_text,
            is_fallback=is_fallback, timestamp=now,
        )
        risk = RiskScore(
            event_id=state["event_id"],
            estimated_intensity=state.get("estimated_intensity", 0.0),
            aftershock_prob_72h=state.get("aftershock_prob_72h", 0.0),
            tsunami_flag=state.get("tsunami_flag", False),
            severity=severity, computed_at=now,
        )
        route = EvacuationRoute(
            event_id=state["event_id"],
            danger_radius_km=state.get("danger_radius_km", 10.0),
            safe_direction=state.get("safe_direction", ""),
            notes=state.get("notes", ""),
            generated_at=now,
            latitude=state.get("latitude"),
            longitude=state.get("longitude"),
        )
        await db.save_alert(alert, risk, route)
        logger.info("[Personal] 保存完了: %s severity=%s fallback=%s",
                    state["event_id"], severity, is_fallback)
        return {"ja_text": ja_text, "en_text": en_text, "is_fallback": is_fallback}
    except Exception as e:
        logger.error("[Personal] エラー: %s", e)
        return {"error": f"personal: {e}"}
