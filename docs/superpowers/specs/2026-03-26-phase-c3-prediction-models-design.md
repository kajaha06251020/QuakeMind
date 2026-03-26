# Phase C3: 予測モデル — ETAS / クーロン応力 / 前震パターン / 連鎖確率 / 時系列予測

## Goal

科学的な地震予測モデル5つを実装し API で公開する。確率的予測（「何倍高まっているか」）のアプローチを取る。

## アルゴリズム

### 1. ETAS 余震モデル

改良大森公式ベースの余震発生率予測。日本域の標準パラメータ（固定値）で開始。

```
λ(t) = μ + Σ K * exp(α(Mi - Mc)) / (t - ti + c)^p
```

パラメータ（Ogata 1988, 日本域標準値）:
- μ = 0.5 (件/日, 背景発生率)
- K = 0.05
- α = 1.0
- c = 0.01 (日)
- p = 1.1

入力: イベントリスト + 予測時刻
出力: 今後24/48/72時間の予測発生数と確率

### 2. クーロン応力変化（ΔCFS）

Okada (1992) の半無限弾性体モデルの簡易版。断層パラメータは震源メカニズムから推定。

ΔCFS = Δτ + μ' * Δσn

簡易実装: 点震源近似で、受け手断層を仮定して応力変化を計算。
- 正のΔCFS: 地震を促進（滑りやすくなる）
- 負のΔCFS: 地震を抑制

### 3. 前震パターンマッチング

過去の大地震（M6+）の直前30日間の活動パターンを「テンプレート」として保存し、現在の活動との類似度をコサイン類似度で計算。

特徴ベクトル: [日別イベント数の30次元ベクトル] を正規化

### 4. 連鎖確率マップ

ETAS モデルの空間拡張。各グリッドセル（0.5度格子）での今後24時間の発生確率を計算。

### 5. 時系列予測

指数平滑法（Holt-Winters）で日別地震発生数を予測。外部ライブラリ不要（numpy で実装）。

## API エンドポイント

```
GET /prediction/etas-forecast
  ?region=東京都&hours=72
  → {"forecast_hours": 72, "expected_events": 3.2, "probability_m4_plus": 0.15}

GET /prediction/coulomb-stress
  ?event_id=xxx
  → {"source_event": {...}, "stress_changes": [{"lat": ..., "lon": ..., "delta_cfs_bar": ...}]}

GET /prediction/foreshock-match
  ?region=東京都
  → {"similarity_score": 0.72, "matched_template": "2011-tohoku-precursor", "alert_level": "elevated"}

GET /prediction/chain-probability
  ?hours=24
  → {"grid": [{"lat": ..., "lon": ..., "probability": ...}], "resolution_deg": 0.5}

GET /prediction/timeseries-forecast
  ?region=東京都&forecast_days=7
  → {"forecast": [{"date": "2026-03-27", "expected_count": 1.2}, ...]}
```

## ファイル構成

```
app/usecases/etas.py                    -- ETAS 余震モデル
app/usecases/coulomb.py                 -- クーロン応力変化
app/usecases/foreshock_matcher.py       -- 前震パターンマッチング
app/usecases/chain_probability.py       -- 連鎖確率マップ
app/usecases/timeseries_forecast.py     -- 時系列予測
app/interfaces/prediction_router.py     -- エンドポイント5つ
tests/test_etas.py
tests/test_coulomb.py
tests/test_foreshock_matcher.py
tests/test_chain_probability.py
tests/test_timeseries_forecast.py
tests/test_prediction_api.py
```

## 完了条件

- 5エンドポイントが動作する
- ETAS が余震発生率を確率的に予測できる
- クーロン応力が応力変化マップを生成できる
- 前震パターンが過去の大地震前兆との類似度を返す
- 連鎖確率がグリッド上の発生確率を返す
- 時系列予測が日別予測を返す
- 全テスト PASSED
