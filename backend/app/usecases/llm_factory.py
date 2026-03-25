"""LLMプロバイダーのファクトリーとフォールバック機構。"""
import logging

from app.config import settings
from app.domain.llm_provider import LLMProvider, LLMError
from app.infrastructure.local_llm_provider import LocalLLMProvider
from app.infrastructure.claude_provider import ClaudeProvider

logger = logging.getLogger(__name__)


def _get_provider() -> LLMProvider:
    if settings.llm_provider == "local":
        return LocalLLMProvider(
            base_url=settings.local_llm_base_url,
            timeout=settings.local_llm_timeout,
        )
    return ClaudeProvider()


def _get_fallback_provider() -> LLMProvider:
    return ClaudeProvider()


def _should_fallback() -> bool:
    return (
        settings.llm_provider == "local"
        and settings.local_llm_fallback_to_claude
    )


async def generate_alert_with_fallback(
    magnitude: float,
    depth: float,
    location: str,
    severity: str,
    safe_direction: str = "",
    notes: str = "",
) -> tuple[str, str, bool]:
    """アラート文を生成する。(ja_text, en_text, is_fallback) を返す。"""
    provider = _get_provider()
    try:
        ja, en = await provider.generate_alert_texts(
            magnitude, depth, location, severity, safe_direction, notes,
        )
        return ja, en, False
    except Exception as e:
        logger.warning("[LLMFactory] プライマリ失敗: %s", e)
        if _should_fallback():
            logger.info("[LLMFactory] Claudeへフォールバック")
            fallback = _get_fallback_provider()
            ja, en = await fallback.generate_alert_texts(
                magnitude, depth, location, severity, safe_direction, notes,
            )
            return ja, en, True
        raise


async def generate_notes_with_fallback(
    region: str,
    magnitude: float,
    depth_km: float,
    tsunami_flag: bool,
) -> tuple[str, bool]:
    """避難注意事項を生成する。(notes, is_fallback) を返す。"""
    provider = _get_provider()
    try:
        notes = await provider.generate_notes(region, magnitude, depth_km, tsunami_flag)
        return notes, False
    except Exception as e:
        logger.warning("[LLMFactory] プライマリ失敗: %s", e)
        if _should_fallback():
            logger.info("[LLMFactory] Claudeへフォールバック")
            fallback = _get_fallback_provider()
            notes = await fallback.generate_notes(region, magnitude, depth_km, tsunami_flag)
            return notes, True
        raise
