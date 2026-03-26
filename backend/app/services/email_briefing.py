"""自動メールブリーフィング。

日次/週次の地震活動サマリをメールで配信する。
実際の送信には SendGrid/Resend のAPIキーが必要。
ここではメール本文の生成とSendGrid送信ロジックを実装。
"""
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def generate_briefing_email(briefing_data: dict) -> dict:
    """ブリーフィングデータからメール用 HTML を生成する。"""
    total = briefing_data.get("total_events", 0)
    max_mag = briefing_data.get("max_magnitude", 0)
    summary = briefing_data.get("summary", "データなし")
    highlights = briefing_data.get("highlights", [])
    period = briefing_data.get("period_days", 1)

    highlights_html = "".join(f"<li>{h}</li>" for h in highlights)

    html = f"""
    <html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>QuakeMind 地震活動ブリーフィング</h2>
    <p style="color: #666;">{datetime.now(timezone.utc).strftime('%Y-%m-%d')} / 過去{period}日間</p>
    <hr>
    <p><strong>概要:</strong> {summary}</p>
    <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 8px; border: 1px solid #ddd;">総イベント数</td><td style="padding: 8px; border: 1px solid #ddd;">{total}</td></tr>
        <tr><td style="padding: 8px; border: 1px solid #ddd;">最大マグニチュード</td><td style="padding: 8px; border: 1px solid #ddd;">M{max_mag}</td></tr>
    </table>
    <h3>注目点</h3>
    <ul>{highlights_html}</ul>
    <hr>
    <p style="color: #999; font-size: 12px;">QuakeMind Automated Briefing</p>
    </body></html>
    """
    return {
        "subject": f"QuakeMind ブリーフィング - M{max_mag} / {total}件 ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})",
        "html": html.strip(),
    }


async def send_email_sendgrid(
    to_email: str,
    subject: str,
    html_content: str,
    api_key: str,
    from_email: str = "noreply@quakemind.app",
) -> dict:
    """SendGrid API v3 でメールを送信する。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": from_email},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_content}],
                },
            )
            if resp.status_code in (200, 202):
                return {"status": "sent", "to": to_email}
            else:
                return {"status": "error", "code": resp.status_code, "detail": resp.text}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
