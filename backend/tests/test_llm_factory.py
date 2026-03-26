"""LLMFactory のテスト。"""
import pytest
from unittest.mock import AsyncMock, patch
from app.usecases.llm_factory import generate_alert_with_fallback, generate_notes_with_fallback
from app.domain.llm_provider import LLMError


@pytest.mark.asyncio
async def test_generate_alert_local_success():
    """ローカルLLMが成功すればそのまま返す。"""
    mock_provider = AsyncMock()
    mock_provider.generate_alert_texts.return_value = ("地震です", "Earthquake")

    with patch("app.usecases.llm_factory._get_provider", return_value=mock_provider):
        ja, en, is_fallback = await generate_alert_with_fallback(6.0, 10.0, "東京都", "HIGH")

    assert ja == "地震です"
    assert en == "Earthquake"
    assert is_fallback is False


@pytest.mark.asyncio
async def test_generate_alert_fallback_to_claude():
    """ローカルLLMが失敗→Claudeにフォールバック。"""
    mock_local = AsyncMock()
    mock_local.generate_alert_texts.side_effect = LLMError("server down")
    mock_claude = AsyncMock()
    mock_claude.generate_alert_texts.return_value = ("Claude地震", "Claude EQ")

    with (
        patch("app.usecases.llm_factory._get_provider", return_value=mock_local),
        patch("app.usecases.llm_factory._get_fallback_provider", return_value=mock_claude),
        patch("app.usecases.llm_factory._should_fallback", return_value=True),
    ):
        ja, en, is_fallback = await generate_alert_with_fallback(6.0, 10.0, "東京都", "HIGH")

    assert ja == "Claude地震"
    assert en == "Claude EQ"
    assert is_fallback is True


@pytest.mark.asyncio
async def test_generate_alert_no_fallback_raises():
    """フォールバック無効時はLLMErrorがそのまま伝播する。"""
    mock_local = AsyncMock()
    mock_local.generate_alert_texts.side_effect = LLMError("server down")

    with (
        patch("app.usecases.llm_factory._get_provider", return_value=mock_local),
        patch("app.usecases.llm_factory._should_fallback", return_value=False),
    ):
        with pytest.raises(LLMError):
            await generate_alert_with_fallback(6.0, 10.0, "東京都", "HIGH")


@pytest.mark.asyncio
async def test_generate_notes_local_success():
    mock_provider = AsyncMock()
    mock_provider.generate_notes.return_value = "・余震に注意"

    with patch("app.usecases.llm_factory._get_provider", return_value=mock_provider):
        notes, is_fallback = await generate_notes_with_fallback("宮城県沖", 7.3, 10.0, True)

    assert "余震" in notes
    assert is_fallback is False


@pytest.mark.asyncio
async def test_generate_notes_fallback_to_claude():
    mock_local = AsyncMock()
    mock_local.generate_notes.side_effect = LLMError("timeout")
    mock_claude = AsyncMock()
    mock_claude.generate_notes.return_value = "・高台に避難"

    with (
        patch("app.usecases.llm_factory._get_provider", return_value=mock_local),
        patch("app.usecases.llm_factory._get_fallback_provider", return_value=mock_claude),
        patch("app.usecases.llm_factory._should_fallback", return_value=True),
    ):
        notes, is_fallback = await generate_notes_with_fallback("宮城県沖", 7.3, 10.0, True)

    assert "高台" in notes
    assert is_fallback is True
