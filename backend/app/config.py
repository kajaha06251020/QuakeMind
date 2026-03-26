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

    # 状態エビクション
    max_events: int = 100
    max_seen_ids: int = 10000

    # データベース
    database_url: str = "postgresql+asyncpg://quakemind:quakemind_dev@localhost:5432/quakemind"
    database_url_test: str = "sqlite+aiosqlite://"

    # Webhook 通知
    webhook_urls: list[str] = []
    webhook_timeout: float = 5.0

    # USGS Earthquake Catalog API
    usgs_enabled: bool = True
    usgs_api_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    usgs_japan_bbox: list[float] = [24.0, 46.0, 122.0, 154.0]  # [min_lat, max_lat, min_lon, max_lon]

    # 気象庁 XML 電文
    jma_xml_enabled: bool = False   # デフォルト無効（Atom Feed の解析に追加コストあり）
    jma_xml_feed_url: str = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

    # NASA GUARDIAN TEC 異常監視
    guardian_enabled: bool = False
    guardian_api_url: str = ""  # 本番環境で設定する

    # POSEIDON Dataset (HuggingFace)
    poseidon_enabled: bool = False   # 初回ロードに時間がかかるためデフォルト無効
    poseidon_dataset_name: str = "JoshuaCarterResearch/POSEIDON"
    poseidon_sample_limit: int = 10000  # 日本周辺からサンプリングする最大件数

    # LLMプロバイダー
    llm_provider: str = "local"          # "local" | "claude"
    local_llm_base_url: str = "http://127.0.0.1:8081"
    local_llm_timeout: float = 120.0
    local_llm_fallback_to_claude: bool = True


settings = Settings()


def configure_langsmith() -> None:
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
