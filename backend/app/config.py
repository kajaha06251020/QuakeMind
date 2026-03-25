from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"
    claude_max_retries: int = 3

    # LangSmith（任意）
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "quakemind"

    # API 認証
    api_key: str = "change-me-before-deploy"

    # データソース
    p2p_api_url: str = "https://api.p2pquake.net/v2/history"
    jma_timeout: float = 10.0
    poll_interval_seconds: int = 60
    p2p_ws_url: Optional[str] = None   # 設定すると WebSocket モードで動作、未設定は HTTP ポーリング
    p2p_ws_reconnect_delay: int = 5

    # 地震検知閾値
    magnitude_threshold: float = 4.0

    # SQLite 永続化
    db_path: str = "quakemind.db"

    # 状態エビクション
    max_events: int = 100
    max_seen_ids: int = 10000

    # Webhook 通知
    webhook_urls: list[str] = []
    webhook_timeout: float = 5.0


settings = Settings()


def configure_langsmith() -> None:
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
