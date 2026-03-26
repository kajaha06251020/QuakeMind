"""PostgreSQL バックアップスクリプト。

使い方: cd backend && .venv/Scripts/python -m scripts.db_backup
環境変数 DATABASE_URL からDB接続情報を取得し pg_dump を実行。
ローカルファイルに保存。S3アップロードは将来対応。
"""
import os
import subprocess
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_BACKUP_DIR = "backups"


def parse_database_url(url: str) -> dict:
    """DATABASE_URL からホスト/ポート/DB名/ユーザー/パスワードを抽出する。"""
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": (parsed.path or "/quakemind").lstrip("/"),
        "user": parsed.username or "quakemind",
        "password": parsed.password or "",
    }


def create_backup(database_url: str | None = None) -> dict:
    """pg_dump でバックアップを作成する。"""
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL", "")

    if not database_url:
        return {"error": "DATABASE_URL が設定されていません"}

    db_info = parse_database_url(database_url)

    os.makedirs(_BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{_BACKUP_DIR}/quakemind_{timestamp}.sql"

    env = os.environ.copy()
    env["PGPASSWORD"] = db_info["password"]

    cmd = [
        "pg_dump",
        "-h", db_info["host"],
        "-p", str(db_info["port"]),
        "-U", db_info["user"],
        "-d", db_info["database"],
        "-f", filename,
        "--no-owner",
        "--no-privileges",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
        if result.returncode != 0:
            return {"error": f"pg_dump failed: {result.stderr}", "filename": filename}

        file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        logger.info("[Backup] 完了: %s (%d bytes)", filename, file_size)
        return {
            "status": "success",
            "filename": filename,
            "size_bytes": file_size,
            "timestamp": timestamp,
        }
    except FileNotFoundError:
        return {"error": "pg_dump が見つかりません。PostgreSQL クライアントをインストールしてください。"}
    except subprocess.TimeoutExpired:
        return {"error": "pg_dump がタイムアウトしました（300秒）"}


def main():
    from app.config import settings
    result = create_backup(settings.database_url)
    if "error" in result:
        logger.error("[Backup] エラー: %s", result["error"])
    else:
        logger.info("[Backup] %s", result)


if __name__ == "__main__":
    main()
