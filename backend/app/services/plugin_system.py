"""プラグインアーキテクチャ。新しい分析モジュールを動的に追加する。"""
import importlib, logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

_plugins: dict[str, dict] = {}

def register_plugin(name: str, module_path: str, description: str = "") -> dict:
    """プラグインを登録する。"""
    try:
        mod = importlib.import_module(module_path)
        _plugins[name] = {"module": mod, "path": module_path, "description": description, "registered_at": datetime.now(timezone.utc).isoformat()}
        logger.info("[Plugin] 登録: %s (%s)", name, module_path)
        return {"status": "registered", "name": name, "module": module_path}
    except ImportError as e:
        return {"status": "error", "name": name, "error": str(e)}

def get_plugin(name: str):
    entry = _plugins.get(name)
    return entry["module"] if entry else None

def list_plugins() -> dict:
    return {"plugins": {k: {"path": v["path"], "description": v["description"], "registered_at": v["registered_at"]} for k, v in _plugins.items()}, "total": len(_plugins)}

def execute_plugin(name: str, function_name: str, *args, **kwargs):
    mod = get_plugin(name)
    if mod is None: return {"error": f"プラグイン '{name}' が見つかりません"}
    func = getattr(mod, function_name, None)
    if func is None: return {"error": f"関数 '{function_name}' が見つかりません"}
    return func(*args, **kwargs)
