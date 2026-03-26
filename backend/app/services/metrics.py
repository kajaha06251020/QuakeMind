"""Prometheus メトリクス収集。"""
import time
import logging
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# カウンター
REQUEST_COUNT = Counter("quakemind_requests_total", "Total API requests", ["method", "endpoint", "status"])
DATA_SOURCE_FETCH_COUNT = Counter("quakemind_data_source_fetches_total", "Data source fetch count", ["source", "status"])
EVENTS_PROCESSED = Counter("quakemind_events_processed_total", "Events processed by pipeline")
ALERTS_GENERATED = Counter("quakemind_alerts_generated_total", "Alerts generated", ["severity"])

# ヒストグラム
REQUEST_LATENCY = Histogram("quakemind_request_duration_seconds", "Request latency", ["endpoint"])
LLM_LATENCY = Histogram("quakemind_llm_duration_seconds", "LLM response time", ["provider"])

# ゲージ
ACTIVE_CONNECTIONS = Gauge("quakemind_active_sse_connections", "Active SSE connections")
LAST_FETCH_TIMESTAMP = Gauge("quakemind_last_fetch_timestamp", "Last successful fetch", ["source"])


def get_metrics() -> bytes:
    """Prometheus 形式のメトリクスを返す。"""
    return generate_latest()


def get_content_type() -> str:
    return CONTENT_TYPE_LATEST
