"""LLMProvider Protocol のテスト。"""
from app.domain.llm_provider import LLMProvider, LLMError


def test_llm_error_is_exception():
    err = LLMError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_llm_provider_is_runtime_checkable():
    """Protocol が runtime_checkable であること。"""

    class FakeProvider:
        async def generate_alert_texts(
            self, magnitude: float, depth: float, location: str, severity: str,
            safe_direction: str = "", notes: str = "",
        ) -> tuple[str, str]:
            return ("ja", "en")

        async def generate_notes(
            self, region: str, magnitude: float, depth_km: float, tsunami_flag: bool,
        ) -> str:
            return "notes"

    assert isinstance(FakeProvider(), LLMProvider)


def test_non_conforming_class_fails_check():
    """メソッドが足りないクラスは LLMProvider ではない。"""

    class NotAProvider:
        pass

    assert not isinstance(NotAProvider(), LLMProvider)


import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.infrastructure.claude_provider import ClaudeProvider
from app.domain.llm_provider import LLMProvider, LLMError


def test_claude_provider_conforms_to_protocol():
    with patch("app.infrastructure.claude_provider.AsyncAnthropic"):
        provider = ClaudeProvider()
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_claude_generate_alert_texts_success():
    with patch("app.infrastructure.claude_provider.AsyncAnthropic") as MockAnthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"ja_text": "地震です", "en_text": "Earthquake"}')]
        )
        MockAnthropic.return_value = mock_client
        provider = ClaudeProvider()

    ja, en = await provider.generate_alert_texts(6.0, 10.0, "東京都", "HIGH", "北東方向", "余震注意")
    assert ja == "地震です"
    assert en == "Earthquake"


@pytest.mark.asyncio
async def test_claude_generate_alert_texts_api_failure():
    with patch("app.infrastructure.claude_provider.AsyncAnthropic") as MockAnthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("API down")
        MockAnthropic.return_value = mock_client
        provider = ClaudeProvider()

    with pytest.raises(LLMError, match="Claude API エラー"):
        await provider.generate_alert_texts(6.0, 10.0, "東京都", "HIGH")


@pytest.mark.asyncio
async def test_claude_generate_notes_success():
    with patch("app.infrastructure.claude_provider.AsyncAnthropic") as MockAnthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="・余震に注意\n・津波に注意")]
        )
        MockAnthropic.return_value = mock_client
        provider = ClaudeProvider()

    notes = await provider.generate_notes("宮城県沖", 7.3, 10.0, True)
    assert "余震" in notes


import httpx
from app.infrastructure.local_llm_provider import LocalLLMProvider


def test_local_provider_conforms_to_protocol():
    provider = LocalLLMProvider()
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_local_generate_alert_texts_success(httpx_mock):
    """正常系: 思考トークン + JSON を返すケース。"""
    provider = LocalLLMProvider(base_url="http://localhost:9999")

    raw_content = (
        '<SPECIAL_17>\nLet me think about this earthquake...\n<SPECIAL_12>\n'
        '{"ja_text": "東京都で震度5弱の地震", "en_text": "Intensity 5- earthquake in Tokyo"}'
    )
    httpx_mock.add_response(
        url="http://localhost:9999/completion",
        json={"content": raw_content},
    )

    ja, en = await provider.generate_alert_texts(6.0, 10.0, "東京都", "HIGH")
    assert ja == "東京都で震度5弱の地震"
    assert en == "Intensity 5- earthquake in Tokyo"


@pytest.mark.asyncio
async def test_local_generate_alert_texts_no_json(httpx_mock):
    """JSONが含まれないレスポンスはLLMErrorになる。"""
    provider = LocalLLMProvider(base_url="http://localhost:9999")
    httpx_mock.add_response(
        url="http://localhost:9999/completion",
        json={"content": "I cannot generate alerts."},
    )

    with pytest.raises(LLMError, match="JSON"):
        await provider.generate_alert_texts(6.0, 10.0, "東京都", "HIGH")


@pytest.mark.asyncio
async def test_local_generate_alert_texts_connection_error(httpx_mock):
    """接続エラーはLLMErrorになる。"""
    provider = LocalLLMProvider(base_url="http://localhost:9999")
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    with pytest.raises(LLMError, match="ローカルLLM"):
        await provider.generate_alert_texts(6.0, 10.0, "東京都", "HIGH")


@pytest.mark.asyncio
async def test_local_generate_notes_success(httpx_mock):
    provider = LocalLLMProvider(base_url="http://localhost:9999")
    raw_content = (
        '<SPECIAL_17>\nThinking...\n<SPECIAL_12>\n'
        '・余震に注意してください\n・高台に避難してください'
    )
    httpx_mock.add_response(
        url="http://localhost:9999/completion",
        json={"content": raw_content},
    )

    notes = await provider.generate_notes("宮城県沖", 7.3, 10.0, True)
    assert "余震" in notes
