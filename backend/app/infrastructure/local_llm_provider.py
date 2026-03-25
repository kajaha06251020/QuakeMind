"""llama.cpp /completion エンドポイント経由のローカルLLMプロバイダー。

/v1/chat/completions は Nemotron 推論モデルの特殊トークンで 500 エラーになるため、
/completion + 手動プロンプト構築 + 正規表現JSON抽出 で対処する。
"""
import json
import logging
import re

import httpx

from app.domain.llm_provider import LLMError

logger = logging.getLogger(__name__)

_ALERT_SYSTEM = (
    "You are a concise emergency earthquake alert system for Japan. "
    "Output ONLY valid JSON with keys ja_text and en_text. "
    "Japanese text must be natural and calm, not alarmist."
)

_NOTES_SYSTEM = "あなたは防災情報アシスタントです。簡潔かつ正確に回答してください。"


def _build_prompt(system: str, user: str) -> str:
    """Nemotron 用のプロンプトを構築する。"""
    return (
        f"<extra_id_0>System\n{system}\n"
        f"<extra_id_1>User\n{user}\n"
        f"<extra_id_1>Assistant\n"
    )


def _strip_thinking(text: str) -> str:
    """推論モデルの思考トークンを除去し、最終回答部分のみ返す。"""
    marker = "<SPECIAL_12>"
    idx = text.rfind(marker)
    if idx >= 0:
        return text[idx + len(marker):].strip()
    return text.strip()


def _extract_json(text: str) -> dict:
    """テキストから最初の JSON オブジェクトを抽出する。"""
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m is None:
        raise LLMError(f"JSON が見つかりません: {text[:200]}")
    return json.loads(m.group(0))


class LocalLLMProvider:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8081",
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout

    async def _complete(self, system: str, user: str) -> str:
        """/completion エンドポイントでテキスト生成し、思考部分を除去して返す。"""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/completion",
                    json={
                        "prompt": _build_prompt(system, user),
                        "temperature": 0.1,
                        "n_predict": 2048,
                        "stop": ["<extra_id_0>", "<extra_id_1>"],
                    },
                )
                resp.raise_for_status()
                raw = resp.json().get("content", "")
                return _strip_thinking(raw)
        except httpx.HTTPStatusError as e:
            raise LLMError(f"ローカルLLM HTTP エラー: {e}") from e
        except httpx.ConnectError as e:
            raise LLMError(f"ローカルLLM 接続エラー: {e}") from e
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"ローカルLLM エラー: {e}") from e

    async def generate_alert_texts(
        self,
        magnitude: float,
        depth: float,
        location: str,
        severity: str,
        safe_direction: str = "",
        notes: str = "",
    ) -> tuple[str, str]:
        context = f"深刻度{severity}"
        if safe_direction:
            context += f" 避難方向:{safe_direction}"
        user_msg = (
            f"地震情報: M{magnitude:.1f} 深さ{depth:.0f}km {location} {context}。"
            f'JSON形式 {{"ja_text": "...", "en_text": "..."}} で生成してください。'
        )
        text = await self._complete(_ALERT_SYSTEM, user_msg)
        data = _extract_json(text)
        ja = data.get("ja_text")
        en = data.get("en_text")
        if not ja or not en:
            raise LLMError(f"JSON にキーが不足: {data}")
        return ja, en

    async def generate_notes(
        self,
        region: str,
        magnitude: float,
        depth_km: float,
        tsunami_flag: bool,
    ) -> str:
        tsunami_text = "あり" if tsunami_flag else "なし"
        user_msg = (
            f"以下の地震情報をもとに、避難時の注意事項を3点以内で簡潔に述べてください。\n"
            f"- 地域: {region}\n- マグニチュード: {magnitude}\n"
            f"- 震源深度: {depth_km}km\n- 津波リスク: {tsunami_text}\n"
            f"箇条書きで、各項目50文字以内。"
        )
        text = await self._complete(_NOTES_SYSTEM, user_msg)
        if not text:
            raise LLMError("ローカルLLM: 空の応答")
        return text
