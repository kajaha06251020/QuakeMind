"""モデルバージョニング + 再現性保証。"""
import logging, hashlib, json
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

_versions: list[dict] = []

def record_analysis(analysis_name: str, parameters: dict, results: dict, code_version: str = "1.0") -> dict:
    entry = {
        "id": hashlib.md5(json.dumps({"name": analysis_name, "params": parameters, "time": datetime.now(timezone.utc).isoformat()}).encode()).hexdigest()[:12],
        "analysis": analysis_name, "parameters": parameters,
        "results_hash": hashlib.md5(json.dumps(results, sort_keys=True, default=str).encode()).hexdigest()[:16],
        "code_version": code_version, "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _versions.append(entry)
    return entry

def get_version_history(analysis_name: str | None = None, limit: int = 20) -> list[dict]:
    filtered = _versions if not analysis_name else [v for v in _versions if v["analysis"] == analysis_name]
    return filtered[-limit:]

def verify_reproducibility(entry_id: str, current_results: dict) -> dict:
    entry = next((v for v in _versions if v["id"] == entry_id), None)
    if not entry: return {"error": "エントリが見つかりません"}
    current_hash = hashlib.md5(json.dumps(current_results, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return {"reproducible": current_hash == entry["results_hash"], "original_hash": entry["results_hash"], "current_hash": current_hash}
