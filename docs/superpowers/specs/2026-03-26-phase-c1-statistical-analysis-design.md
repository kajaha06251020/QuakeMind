# Phase C1: 統計分析基盤 — 設計スペック

## Goal

既存の seismic_analysis.py の解析関数を earthquake_events テーブルのデータに接続し、地域別・期間別の統計分析 API を公開する。新規にフラクタル次元解析と時系列追跡を追加する。

## 既存の解析機能（seismic_analysis.py に実装済み）

- Gardner-Knopoff デクラスタリング
- Mc 推定（MAXC, MBS-WW, b-positive の3手法）
- b値 MLE (Aki 1965) + Shi & Bolt δb
- a値 (Gutenberg-Richter)
- 簡易 PSHA

## 新規追加する解析機能

### フラクタル次元解析（D値）

震源分布の空間的集中度。相関次元 D2 をボックスカウンティング法で計算。

```
D2 = lim(log C(r) / log r)   r → 0
C(r) = (2/N(N-1)) * Σ H(r - |xi - xj|)
```

D値が低い（< 2.0）ほど震源が空間的に集中 → 応力集中の兆候。

### a値・b値の時系列追跡

earthquake_events のデータをスライディングウィンドウ（例: 90日、30日ずらし）で区切り、各ウィンドウの a値/b値を計算して時系列データとして返す。b値の急低下は大地震の前兆とされる。

## API エンドポイント

### GET /analysis/statistics — 地域別統計

```
GET /analysis/statistics?region=東京都&start=2026-01-01&end=2026-03-26

Response:
{
  "region": "東京都",
  "period": {"start": "2026-01-01", "end": "2026-03-26"},
  "total_events": 156,
  "magnitude_distribution": {
    "min": 1.2, "max": 6.1, "mean": 3.4, "median": 3.1
  },
  "depth_distribution": {
    "min": 5.0, "max": 120.0, "mean": 35.2, "median": 28.0
  },
  "frequency_by_hour": [0, 2, 1, ...],  // 24要素
  "frequency_by_magnitude_bin": {"2.0": 45, "3.0": 67, ...}
}
```

### GET /analysis/gutenberg-richter — GR解析

```
GET /analysis/gutenberg-richter?region=東京都&start=2026-01-01&end=2026-03-26

Response:
{
  "mc": 2.1,
  "b_value": 0.95,
  "b_uncertainty": 0.08,
  "a_value": 4.32,
  "n_events": 120,
  "mc_method": "MBS-WW"
}
```

### GET /analysis/b-value-timeseries — b値時系列

```
GET /analysis/b-value-timeseries?region=東京都&window_days=90&step_days=30

Response:
{
  "region": "東京都",
  "window_days": 90,
  "step_days": 30,
  "timeseries": [
    {"start": "2025-12-01", "end": "2026-02-28", "b_value": 1.02, "a_value": 3.8, "n_events": 45},
    {"start": "2026-01-01", "end": "2026-03-31", "b_value": 0.88, "a_value": 4.1, "n_events": 52},
    ...
  ]
}
```

### GET /analysis/fractal-dimension — フラクタル次元

```
GET /analysis/fractal-dimension?region=東京都&start=2026-01-01&end=2026-03-26

Response:
{
  "region": "東京都",
  "d2": 1.65,
  "n_events": 120,
  "interpretation": "空間的に集中（応力集中の可能性）"
}
```

### GET /analysis/decluster — デクラスタリング

```
GET /analysis/decluster?region=東京都&start=2026-01-01&end=2026-03-26

Response:
{
  "method": "Gardner-Knopoff",
  "n_total": 156,
  "n_mainshocks": 89,
  "n_aftershocks": 67,
  "aftershock_ratio": 0.43
}
```

## ファイル構成

### 新規

```
app/usecases/statistics.py           -- earthquake_events → seismic_analysis 橋渡し
app/usecases/fractal.py              -- フラクタル次元解析
app/usecases/b_value_tracker.py      -- b値/a値の時系列追跡
app/interfaces/statistics_router.py  -- 統計分析 API エンドポイント群
tests/test_statistics.py
tests/test_fractal.py
tests/test_b_value_tracker.py
tests/test_statistics_api.py
```

### 変更

```
app/interfaces/api.py                -- statistics_router を include
app/infrastructure/db.py             -- get_events_for_analysis() 追加（EarthquakeRecord形式で返す）
```

## データフロー

```
GET /analysis/* リクエスト
  → statistics_router
    → db.get_events_for_analysis(region, start, end)
      → earthquake_events テーブルから取得
      → EarthquakeRecord 形式に変換
    → seismic_analysis.py / fractal.py / b_value_tracker.py で計算
    → JSON レスポンス
```

## テスト戦略

- 新規アルゴリズム（フラクタル次元、時系列追跡）はユニットテスト
- API エンドポイントは async_client + seed data でテスト
- 既存の seismic_analysis.py テストはそのまま維持

## 完了条件

- 5つの分析エンドポイントが動作する
- earthquake_events のデータを使って統計分析ができる
- b値の時系列変化を追跡できる
- フラクタル次元が計算できる
- 全テスト PASSED
