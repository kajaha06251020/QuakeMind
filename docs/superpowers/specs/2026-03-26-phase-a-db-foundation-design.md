# Phase A: データベース基盤 — PostgreSQL移行 + 時系列データ + ユーザー設定

## Goal

SQLite から PostgreSQL (SQLAlchemy async + Alembic) に移行し、全地震イベントの時系列保存とユーザー設定テーブルを追加する。Phase B（データソース拡張）・Phase C（バックエンド機能）の土台。

## 技術選定

- **ORM**: SQLAlchemy 2.x (async) — テーブル定義を Python クラスで管理
- **マイグレーション**: Alembic — スキーマ変更の履歴管理
- **ドライバ**: asyncpg（本番 PostgreSQL）、aiosqlite（テスト用 SQLite in-memory）
- **既存 PostgreSQL コンテナ**: docker-compose.yml に定義済み（quakemind:quakemind_dev@localhost:5432/quakemind）

## 既存データの扱い

SQLite の既存データ（seen_events, alerts）は**破棄する**。理由:
- 開発中のテストデータのみで、本番データではない
- スキーマが変わる（PK変更、カラム追加）ため移行スクリプトのコストに見合わない
- PostgreSQL に移行後、新規データから蓄積を開始する

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

1イベントに対して1アラート。`event_id` に UNIQUE 制約を付ける。

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | サロゲートキー |
| event_id | VARCHAR | UNIQUE NOT NULL, FK→earthquake_events.event_id | 地震イベント参照（1:1） |
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

## フィールドマッピング（ドメインモデル → DBカラム）

| ドメインモデル | フィールド | DBテーブル | カラム |
|---------------|-----------|-----------|--------|
| EarthquakeEvent.timestamp | datetime | earthquake_events | occurred_at |
| EarthquakeEvent.source | str | earthquake_events | source |
| AlertMessage.timestamp | datetime | alerts | created_at |
| seen_events (旧 created_at) | — | seen_events | seen_at |

## エラーハンドリング

- **event_store.save_events() 失敗時**: ログ出力して polling loop を継続。イベントは次回ポーリングで再取得される（べき等性は event_id UNIQUE による INSERT ON CONFLICT DO NOTHING で保証）
- **save_alert() 失敗時**: ログ出力、`personal_node` が `{"error": ...}` を返す（既存動作を維持）
- **接続プール枯渇**: SQLAlchemy のデフォルト pool_size=5, max_overflow=10 を使用。polling loop (1接続) + SSE (N接続) + API (M接続) で十分

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
                                 # 既存関数のシグネチャは維持（引数・戻り値の型は同じ）
                                 # database.py から get_session() を import して使う
app/interfaces/api.py            # lifespan 変更、新規エンドポイント3つ追加
app/infrastructure/multi_source.py  # fetch後に event_store.save_events() 呼び出し追加
app/config.py                    # database_url 設定追加、db_path は削除
requirements.txt                 # sqlalchemy[asyncio], asyncpg, alembic 追加
docker-compose.yml               # backend に DATABASE_URL 環境変数追加、backend_data ボリューム削除
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

## event_store.save_events() 仕様

```python
async def save_events(events: list[EarthquakeEvent]) -> int:
    """イベントを earthquake_events に一括保存する。
    event_id が既に存在する場合は無視（INSERT ON CONFLICT DO NOTHING 相当）。
    戻り値: 新規保存した件数。
    """
```

- 同じ event_id が P2P と USGS の両方から来る場合、先に保存されたソースが残る
- バッチ処理: 1回の session で全件 add し、最後に commit

## database.py の責務

```python
# engine と sessionmaker を管理する薄いモジュール
async_engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(async_engine)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

async def init_db() -> None:
    """Alembic を使わないテスト環境用: metadata.create_all()"""
    ...
```

`db.py` は `get_session()` を import してクエリ関数を実装する。

## テスト戦略

- テスト DB は **SQLite in-memory** (`sqlite+aiosqlite://`)
- **既知の制限**: JSONB は SQLite では TEXT 扱い。JSONB 演算子（`->`, `@>`）を使うクエリはテストできない。Phase A では JSONB カラムは保存・取得のみで、検索には使わないため問題なし
- `conftest.py` を async 対応に書き換える:
  - `database.py` の engine を SQLite in-memory に差し替える fixture
  - `Base.metadata.create_all()` でテスト用テーブルを毎回作成
  - `httpx.AsyncClient` + `ASGITransport` で async テストクライアントを使用
- 新規テストファイル:
  - `tests/test_database.py` — セッション管理、テーブル作成
  - `tests/test_event_store.py` — イベント保存、重複無視、バッチ処理
  - `tests/test_settings_api.py` — GET/PUT /settings、デフォルト自動作成
  - `tests/test_events_api.py` — GET /events フィルタ、ページネーション
- 既存テストファイル（`test_api.py`, `test_agents.py` 等）は conftest.py 変更で対応

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
