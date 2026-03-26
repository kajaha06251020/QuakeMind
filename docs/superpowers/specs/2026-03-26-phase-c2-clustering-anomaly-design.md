# Phase C2: クラスタリング + 異常検知 + 静穏化検出

## Goal

earthquake_events のデータを使い、時空間クラスタリング（群発地震検知）、異常活動検知、静穏化検出の3つのアルゴリズムを実装し API で公開する。

## アルゴリズム

### 1. 時空間クラスタリング（DBSCAN）

DBSCAN で時間・空間的に近い地震をクラスタ化。特徴行列は [lat, lon, time_days] を正規化して使用。

- eps: 空間的に約50km + 時間的に約7日 を1つのクラスタとみなす
- min_samples: 3（最低3イベントでクラスタ認定）
- 出力: クラスタID、各クラスタのイベント数・中心座標・期間・最大マグニチュード

### 2. 地震活動の異常検知

過去の平均発生率と直近の発生率を比較し、統計的に有意な活動増加を検出。

- 背景期間: 全期間の平均発生率（件/日）
- 評価期間: 直近N日（デフォルト7日）
- 判定: ポアソン分布の上側確率で p < 0.05 なら「異常」

### 3. 静穏化検出

大地震前に小地震が減少する現象を検出。

- 背景期間の平均発生率と直近期間の発生率を比較
- 直近発生率が背景の50%以下なら「静穏化」フラグ
- 地域ごとに評価

## API エンドポイント

### GET /analysis-advanced/clusters

```json
{
  "n_clusters": 3,
  "noise_events": 12,
  "clusters": [
    {
      "cluster_id": 0,
      "n_events": 15,
      "center_lat": 35.2,
      "center_lon": 139.5,
      "start": "2026-03-20T...",
      "end": "2026-03-25T...",
      "max_magnitude": 5.2
    }
  ]
}
```

### GET /analysis-advanced/anomaly

```json
{
  "region": "東京都",
  "is_anomalous": true,
  "background_rate": 0.8,
  "recent_rate": 3.5,
  "p_value": 0.002,
  "evaluation_days": 7
}
```

### GET /analysis-advanced/quiescence

```json
{
  "region": "東京都",
  "is_quiescent": false,
  "background_rate": 0.8,
  "recent_rate": 0.6,
  "ratio": 0.75,
  "evaluation_days": 30
}
```

## ファイル構成

```
app/usecases/clustering.py              -- DBSCAN クラスタリング
app/usecases/anomaly_detection.py       -- 異常検知 + 静穏化検出
app/interfaces/advanced_analysis_router.py -- エンドポイント3つ
tests/test_clustering.py
tests/test_anomaly_detection.py
tests/test_advanced_analysis_api.py
```

## 完了条件

- 3エンドポイントが動作する
- クラスタリングが群発地震を検出できる
- 異常検知が統計的に有意な活動増加を判定できる
- 静穏化検出が活動低下を判定できる
- 全テスト PASSED
