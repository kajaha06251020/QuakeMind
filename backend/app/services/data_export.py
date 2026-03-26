"""データエクスポートサービス。CSV/GeoJSON/KML 形式。"""
import csv
import io
import json
import logging

from app.domain.seismology import EarthquakeRecord

logger = logging.getLogger(__name__)


def export_csv(events: list[EarthquakeRecord]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_id", "magnitude", "depth_km", "latitude", "longitude", "timestamp"])
    for e in events:
        writer.writerow([e.event_id, e.magnitude, e.depth_km, e.latitude, e.longitude, e.timestamp])
    return output.getvalue()


def export_geojson(events: list[EarthquakeRecord]) -> dict:
    features = []
    for e in events:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [e.longitude, e.latitude]},
            "properties": {
                "event_id": e.event_id,
                "magnitude": e.magnitude,
                "depth_km": e.depth_km,
                "timestamp": e.timestamp,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def export_kml(events: list[EarthquakeRecord]) -> str:
    placemarks = []
    for e in events:
        placemarks.append(
            f"<Placemark><name>M{e.magnitude} {e.event_id}</name>"
            f"<Point><coordinates>{e.longitude},{e.latitude},0</coordinates></Point>"
            f"<description>Depth: {e.depth_km}km, Time: {e.timestamp}</description></Placemark>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        '<name>QuakeMind Export</name>'
        + "".join(placemarks)
        + '</Document></kml>'
    )
