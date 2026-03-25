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
