"""完全監査証跡。全予測・判断の理由と根拠を永続記録。"""
import logging, uuid
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

_audit_log: list[dict] = []

def log_decision(action: str, reason: str, evidence: dict | None = None, actor: str = "system") -> str:
    entry_id = str(uuid.uuid4())[:12]
    _audit_log.append({"id": entry_id, "action": action, "reason": reason, "evidence": evidence, "actor": actor, "timestamp": datetime.now(timezone.utc).isoformat()})
    return entry_id

def get_audit_log(limit: int = 50, action_filter: str | None = None) -> list[dict]:
    filtered = _audit_log if not action_filter else [e for e in _audit_log if action_filter in e["action"]]
    return filtered[-limit:]

def get_decision_context(entry_id: str) -> dict | None:
    return next((e for e in _audit_log if e["id"] == entry_id), None)
