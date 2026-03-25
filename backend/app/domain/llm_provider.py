"""LLMプロバイダーの抽象定義。"""
from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """LLMプロバイダー共通のエラー。"""


@runtime_checkable
class LLMProvider(Protocol):
    async def generate_alert_texts(
        self,
        magnitude: float,
        depth: float,
        location: str,
        severity: str,
        safe_direction: str = "",
        notes: str = "",
    ) -> tuple[str, str]:
        """(ja_text, en_text) を返す。失敗時は LLMError を送出。"""
        ...

    async def generate_notes(
        self,
        region: str,
        magnitude: float,
        depth_km: float,
        tsunami_flag: bool,
    ) -> str:
        """避難注意事項テキストを返す。失敗時は LLMError を送出。"""
        ...
