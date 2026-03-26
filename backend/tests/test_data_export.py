import pytest
from app.domain.seismology import EarthquakeRecord
from app.services.data_export import export_csv, export_geojson, export_kml

def _events():
    return [
        EarthquakeRecord(event_id="e1", magnitude=5.0, latitude=35.0, longitude=139.0, depth_km=10.0, timestamp="2026-03-25T10:00:00Z"),
        EarthquakeRecord(event_id="e2", magnitude=4.0, latitude=34.0, longitude=135.0, depth_km=20.0, timestamp="2026-03-25T09:00:00Z"),
    ]

def test_export_csv():
    result = export_csv(_events())
    assert "event_id" in result
    assert "e1" in result
    assert result.count("\n") >= 3  # header + 2 rows

def test_export_geojson():
    result = export_geojson(_events())
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2
    assert result["features"][0]["geometry"]["type"] == "Point"

def test_export_kml():
    result = export_kml(_events())
    assert "<kml" in result
    assert "M5.0" in result
    assert "<coordinates>" in result
