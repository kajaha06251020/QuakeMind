"""Personal Agent: Claude でエンドユーザー向けアラート文を生成する。"""
import json
import logging
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from config import settings
from state import EventState, AlertMessage, RiskScore, EvacuationRoute
from data import db

logger = logging.getLogger(__name__)

_claude = AsyncAnthropic(
    api_key=settings.anthropic_api_key,
    max_retries=settings.claude_max_retries,
)


def _fallback_alert(state: EventState) -> tuple[str, str]:
    """Claude 障害時のテンプレートアラート。"""
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


async def _generate_alert_with_claude(state: EventState) -> tuple[str, str, bool]:
    """Claude でアラート文を生成する。失敗時はフォールバックを返す。"""
    severity = state.get("severity", "MEDIUM")
    region = state["region"]
    magnitude = state["magnitude"]
    depth_km = state["depth_km"]
    safe_direction = state.get("safe_direction", "安全な場所")
    notes = state.get("notes", "")

    prompt = (
        f"以下の情報からJSON形式で避難アラートを生成してください。\n"
        f"- 地域: {region}, M{magnitude}, 深度{depth_km}km\n"
        f"- 深刻度: {severity}\n"
        f"- 推奨避難方向: {safe_direction}\n"
        f"- 注意事項: {notes}\n\n"
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
        # JSON 部分だけ抽出
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return data["ja_text"], data["en_text"], False
    except Exception as e:
        logger.warning("[Personal] Claude 呼び出し失敗、フォールバック使用: %s", e)
        ja, en = _fallback_alert(state)
        return ja, en, True


async def personal_node(state: EventState) -> dict:
    """LangGraph ノード: アラートを生成して DB に保存する。"""
    if state.get("error"):
        logger.error("[Personal] 上流エラーのためスキップ: %s", state["error"])
        return {}

    try:
        ja_text, en_text, is_llm_fallback = await _generate_alert_with_claude(state)

        # Route Agent でもフォールバックが発生していた場合
        is_fallback = is_llm_fallback or state.get("is_fallback", False)

        now = datetime.now(timezone.utc)
        severity = state.get("severity", "MEDIUM")

        alert = AlertMessage(
            event_id=state["event_id"],
            severity=severity,
            ja_text=ja_text,
            en_text=en_text,
            is_fallback=is_fallback,
            timestamp=now,
        )

        risk = RiskScore(
            event_id=state["event_id"],
            estimated_intensity=state.get("estimated_intensity", 0.0),
            aftershock_prob_72h=state.get("aftershock_prob_72h", 0.0),
            tsunami_flag=state.get("tsunami_flag", False),
            severity=severity,
            computed_at=now,
        )

        route = EvacuationRoute(
            event_id=state["event_id"],
            danger_radius_km=state.get("danger_radius_km", 10.0),
            safe_direction=state.get("safe_direction", ""),
            notes=state.get("notes", ""),
            generated_at=now,
        )

        await db.save_alert(alert, risk, route)

        logger.info(
            "[Personal] アラート保存完了: %s severity=%s fallback=%s",
            state["event_id"], severity, is_fallback,
        )

        return {
            "ja_text": ja_text,
            "en_text": en_text,
            "is_fallback": is_fallback,
        }

    except Exception as e:
        logger.error("[Personal] エラー: %s", e)
        return {"error": f"personal: {e}"}
