"""APIキャッシュ + 結果の差分検出。"""
import hashlib, json, logging, time
logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}
_TTL_SECONDS = 300  # 5分

def cache_key(endpoint: str, params: dict) -> str:
    raw = json.dumps({"e": endpoint, "p": params}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()

def get_cached(endpoint: str, params: dict) -> dict | None:
    key = cache_key(endpoint, params)
    entry = _cache.get(key)
    if entry and time.time() - entry["time"] < _TTL_SECONDS:
        return entry["data"]
    return None

def set_cache(endpoint: str, params: dict, data: dict) -> None:
    key = cache_key(endpoint, params)
    _cache[key] = {"data": data, "time": time.time()}

def invalidate(endpoint: str | None = None) -> int:
    if endpoint is None:
        n = len(_cache); _cache.clear(); return n
    keys = [k for k, v in _cache.items()]  # simplified
    n = len(_cache); _cache.clear(); return n

def cache_stats() -> dict:
    now = time.time()
    valid = sum(1 for v in _cache.values() if now - v["time"] < _TTL_SECONDS)
    return {"total_entries": len(_cache), "valid_entries": valid, "ttl_seconds": _TTL_SECONDS}
