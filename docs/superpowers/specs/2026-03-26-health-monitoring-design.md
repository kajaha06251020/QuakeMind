# Phase C #13: ヘルスモニタリング強化

## Goal

GET /health エンドポイントを追加し、DB接続・LLMサーバー・各データソースの死活状態とアプリのアップタイムを一括で確認できるようにする。

## GET /health レスポンス

```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "started_at": "2026-03-26T10:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 2
    },
    "llm_server": {
      "status": "healthy",
      "provider": "local",
      "base_url": "http://127.0.0.1:8081",
      "latency_ms": 15
    },
    "data_sources": {
      "p2p": {
        "status": "healthy",
        "last_fetch_at": "2026-03-26T10:59:00Z",
        "last_error": null
      },
      "usgs": {
        "status": "healthy",
        "last_fetch_at": "2026-03-26T10:59:00Z",
        "last_error": null
      },
      "jma_xml": {
        "status": "disabled",
        "last_fetch_at": null,
        "last_error": null
      }
    }
  }
}
```

## ステータス判定ルール

- `status`: 全コンポーネント healthy なら `"healthy"`、1つでも unhealthy なら `"degraded"`
- **database**: `SELECT 1` を実行し応答時間を計測。タイムアウト(3秒)で unhealthy
- **llm_server**: config の `llm_provider` が `"local"` の場合、`{base_url}/health` に GET。応答がなければ unhealthy だが全体ステータスは degraded（Claude フォールバックがあるため）。`llm_provider` が `"claude"` の場合は省略
- **data_sources**: `multi_source.py` の fetch 時に最終取得時刻とエラーを記録。disabled のソースは `"disabled"` 表示

## ファイル構成

### 新規

- `app/services/health.py` — ヘルスチェックロジック。DB ping、LLM ping、データソースステータス収集
- `tests/test_health.py` — ヘルスエンドポイントのテスト

### 変更

- `app/interfaces/api.py` — GET /health エンドポイント追加、lifespan で started_at を記録
- `app/infrastructure/multi_source.py` — fetch 結果のステータス（時刻、エラー）をモジュール変数に記録

## データソースステータスの記録方式

`multi_source.py` にモジュールレベルの dict を追加:

```python
_source_status: dict[str, dict] = {}

def get_source_status() -> dict[str, dict]:
    return _source_status.copy()
```

`fetch_all_sources` 内で各ソースの結果を記録:

```python
for name, result in zip(source_names, results):
    if isinstance(result, Exception):
        _source_status[name] = {"last_fetch_at": now, "last_error": str(result)}
    else:
        _source_status[name] = {"last_fetch_at": now, "last_error": None}
```

## テスト戦略

- DB ping: SQLite in-memory で動作確認
- LLM ping: httpx_mock で /health をモック
- データソースステータス: `_source_status` を直接設定してテスト
- 全体ステータス判定: healthy / degraded のパターンテスト

## 完了条件

- GET /health が全コンポーネントの状態を返す
- DB接続エラー時に degraded を返す
- LLMサーバー未起動時に degraded を返す
- データソースの最終取得時刻とエラーが表示される
- 全テスト PASSED
