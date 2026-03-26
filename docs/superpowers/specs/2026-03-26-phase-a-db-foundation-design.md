# Phase A: データベース基盤 — PostgreSQL移行 + 時系列データ + ユーザー設定

## Goal

SQLite から PostgreSQL (SQLAlchemy async + Alembic) に移行し、全地震イベントの時系列保存とユーザー設定テーブルを追加する。Phase B（データソース拡張）・Phase C（バックエンド機能）の土台。

## 技術選定

- **ORM**: SQLAlchemy 2.x (async) — テーブル定義を Python クラスで管理
- **マイグレーション**: Alembic — スキーマ変更の履歴管理
- **ドライバ**: asyncpg（本番 PostgreSQL）、aiosqlite（テスト用 SQLite in-memory）
- **既存 PostgreSQL コンテナ**: docker-compose.yml に定義済み（quakemind:quakemind_dev@localhost:5432/quakemind）

## テーブル設計

### earthquake_events（新規）

全データソースから取得した地震イベントを magnitude_threshold 以下も含めて全件保存する。

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | サロゲートキー |
| event_id | VARCHAR | UNIQUE NOT NULL | データソースの元ID |
| source | VARCHAR | NOT NULL | "p2p" / "usgs" / "jma_xml" |
| magnitude | FLOAT | NOT NULL | マグニチュード |
| depth_km | FLOAT | NOT NULL | 震源深度 (km) |
| latitude | FLOAT | NOT NULL | 緯度 |
| longitude | FLOAT | NOT NULL | 経度 |
| region | VARCHAR | NOT NULL | 地域名 |
| occurred_at | TIMESTAMPTZ | NOT NULL | 地震発生時刻 |
| fetched_at | TIMESTAMPTZ | NOT NULL | システム取得時刻 |

インデックス: `occurred_at`, `region`, `magnitude`

### alerts（既存を拡張）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | サロゲートキー |
| event_id | VARCHAR | NOT NULL, FK→earthquake_events.event_id | 地震イベント参照 |
| severity | VARCHAR | NOT NULL | LOW/MEDIUM/HIGH/CRITICAL |
| ja_text | TEXT | NOT NULL | 日本語アラート文 |
| en_text | TEXT | NOT NULL | 英語アラート文 |
| is_fallback | BOOLEAN | DEFAULT FALSE | フォールバック生成か |
| risk_json | JSONB | | リスクスコア JSON |
| route_json | JSONB | | 避難ルート JSON |
| created_at | TIMESTAMPTZ | NOT NULL | 作成時刻 |

インデックス: `created_at`, `severity`

### seen_events（既存を移行）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| event_id | VARCHAR | PK | 重複チェック用イベントID |
| seen_at | TIMESTAMPTZ | NOT NULL | 検出時刻 |

### user_settings（新規）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | サロゲートキー |
| user_id | VARCHAR | UNIQUE NOT NULL | 当面は "default" |
| min_severity | VARCHAR | DEFAULT "LOW" | 通知する最低深刻度 |
| region_filters | JSONB | DEFAULT '[]' | 監視対象地域リスト |
| notification_channels | JSONB | DEFAULT '[]' | [{type, url/token}, ...] |
| created_at | TIMESTAMPTZ | NOT NULL | 作成時刻 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新時刻 |

## ファイル構成

### 新規ファイル

```
backend/
├── app/infrastructure/
│   ├── database.py              # async engine + async_sessionmaker
│   └── models_db.py             # SQLAlchemy テーブルモデル (4テーブル)
├── app/usecases/
│   └── event_store.py           # イベント全件保存ロジック
├── alembic/
│   ├── env.py                   # async 対応 Alembic 環境
│   └── versions/
│       └── 001_initial.py       # 初期マイグレーション
└── alembic.ini
```

### 変更ファイル

```
app/infrastructure/db.py         # aiosqlite → SQLAlchemy async session に全面書き換え
                                 # 既存関数のシグネチャは維持
app/interfaces/api.py            # lifespan 変更、新規エンドポイント3つ追加
app/infrastructure/multi_source.py  # fetch後に event_store.save_events() 呼び出し追加
app/config.py                    # database_url 設定追加
requirements.txt                 # sqlalchemy[asyncio], asyncpg, alembic 追加
docker-compose.yml               # backend に DATABASE_URL 環境変数追加
```

## データフロー

```
変更前:
  fetch_all_sources() → is_event_seen? → pipeline → save_alert()

変更後:
  fetch_all_sources() → event_store.save_events(全件)
                       → is_event_seen? → pipeline → save_alert()
```

全イベント（magnitude_threshold 以下も含む）を `earthquake_events` に保存してから、既存のフィルタリング・パイプライン処理を行う。

## 新規 API エンドポイント

### GET /events — イベント履歴検索

```
GET /events?limit=50&offset=0&min_magnitude=3.0&region=東京都&start=2026-01-01&end=2026-03-26

Response:
{
  "events": [...],
  "total": 1234,
  "limit": 50,
  "offset": 0
}
```

全フィルタパラメータは任意。

### GET /settings — ユーザー設定取得

```
GET /settings

Response:
{
  "min_severity": "MEDIUM",
  "region_filters": ["東京都", "宮城県"],
  "notification_channels": [{"type": "discord", "url": "https://..."}]
}
```

user_id="default" の設定を返す。存在しなければデフォルト値で自動作成。

### PUT /settings — ユーザー設定更新

```
PUT /settings
Body:
{
  "min_severity": "HIGH",
  "region_filters": ["東京都"],
  "notification_channels": [...]
}

Response: 200 (更新後の設定)
```

## テスト戦略

- テスト DB は **SQLite in-memory** (`sqlite+aiosqlite://`)
- PostgreSQL 固有の JSONB は SQLite の JSON 関数で代替可能
- 既存の `db.py` 関数シグネチャを維持し、テスト側の変更を最小限にする
- 新規テスト: models_db, database, event_store, 新規 API エンドポイント

## config.py 追加設定

```python
database_url: str = "postgresql+asyncpg://quakemind:quakemind_dev@localhost:5432/quakemind"
database_url_test: str = "sqlite+aiosqlite://"
```

## 完了条件

- PostgreSQL でアプリケーションが起動し、全既存機能が動作する
- 全イベントが earthquake_events テーブルに保存される
- GET /events でフィルタ付き検索ができる
- GET/PUT /settings でユーザー設定の取得・更新ができる
- 全テスト PASSED（SQLite in-memory）
- Alembic マイグレーションが正常に適用できる
