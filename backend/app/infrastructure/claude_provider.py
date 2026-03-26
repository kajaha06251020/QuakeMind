"""Claude API を使った LLMProvider 実装。personal.py / route.py から移植。"""
import json
import logging

from anthropic import AsyncAnthropic

from app.config import settings
from app.domain.llm_provider import LLMError

logger = logging.getLogger(__name__)


class ClaudeProvider:
    def __init__(self) -> None:
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=settings.claude_max_retries,
        )

    async def generate_alert_texts(
        self,
        magnitude: float,
        depth: float,
        location: str,
        severity: str,
        safe_direction: str = "",
        notes: str = "",
    ) -> tuple[str, str]:
        prompt = (
            f"以下の情報からJSON形式で避難アラートを生成してください。\n"
            f"- 地域: {location}, M{magnitude}, 深度{depth}km\n"
            f"- 深刻度: {severity}\n"
            f"- 推奨避難方向: {safe_direction or '安全な場所'}\n"
            f"- 注意事項: {notes or 'なし'}\n\n"
            f'出力形式（JSONのみ）:\n'
            f'{{"ja_text": "（日本語、200文字以内）", "en_text": "（English, 150 chars max）"}}'
        )
        try:
            response = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=400,
                system="You are a concise emergency alert system. Output valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            data = json.loads(text[text.find("{"):text.rfind("}") + 1])
            return data["ja_text"], data["en_text"]
        except Exception as e:
            raise LLMError(f"Claude API エラー: {e}") from e

    async def generate_notes(
        self,
        region: str,
        magnitude: float,
        depth_km: float,
        tsunami_flag: bool,
    ) -> str:
        tsunami_text = "あり" if tsunami_flag else "なし"
        prompt = (
            f"以下の地震情報をもとに、避難時の注意事項を3点以内で簡潔に述べてください。\n"
            f"- 地域: {region}\n- マグニチュード: {magnitude}\n"
            f"- 震源深度: {depth_km}km\n- 津波リスク: {tsunami_text}\n"
            f"箇条書きで、各項目50文字以内。"
        )
        try:
            response = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=300,
                system="あなたは防災情報アシスタントです。簡潔かつ正確に回答してください。",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            raise LLMError(f"Claude API エラー: {e}") from e
