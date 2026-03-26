from app.usecases.seismic_gap import analyze_seismic_gaps


def test_gap_analysis():
    result = analyze_seismic_gaps([])
    assert result["analyzed_segments"] > 0
    # 東海は1854年以降大地震なし → 高い確率
    tokai = next(s for s in result["segments"] if s["segment"] == "東海")
    assert tokai["elapsed_years"] > 150
    assert tokai["probability_next_30yr"] > 0


def test_gap_with_events():
    from datetime import datetime, timezone
    from app.domain.seismology import EarthquakeRecord
    events = [EarthquakeRecord(event_id=f"g-{i}", magnitude=5.0, latitude=33.0, longitude=135.0, depth_km=20.0, timestamp=datetime.now(timezone.utc).isoformat()) for i in range(20)]
    result = analyze_seismic_gaps(events)
    # 南海付近にイベントが多い → gap ではない
    nankai = next(s for s in result["segments"] if s["segment"] == "南海")
    assert nankai["nearby_m4_events"] > 0
