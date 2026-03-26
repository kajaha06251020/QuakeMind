import pytest
from app.services.email_briefing import generate_briefing_email, send_email_sendgrid


def test_generate_email():
    data = {"total_events": 15, "max_magnitude": 5.2, "summary": "活発な活動", "highlights": ["M5.2の地震"], "period_days": 1}
    result = generate_briefing_email(data)
    assert "subject" in result
    assert "html" in result
    assert "M5.2" in result["html"]
    assert "QuakeMind" in result["subject"]


@pytest.mark.asyncio
async def test_send_email_mock(httpx_mock):
    import re
    httpx_mock.add_response(url=re.compile(r"https://api\.sendgrid\.com.*"), status_code=202)
    result = await send_email_sendgrid("test@example.com", "Test", "<p>Hi</p>", "fake-key")
    assert result["status"] == "sent"


@pytest.mark.asyncio
async def test_send_email_error(httpx_mock):
    import httpx
    httpx_mock.add_exception(httpx.ConnectError("timeout"))
    result = await send_email_sendgrid("test@example.com", "Test", "<p>Hi</p>", "fake-key")
    assert result["status"] == "error"
