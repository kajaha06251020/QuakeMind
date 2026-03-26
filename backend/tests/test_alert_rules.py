from app.domain.models import EarthquakeEvent
from app.services.alert_rules import AlertRule, evaluate_rules
from datetime import datetime, timezone

def _event(mag=5.0, lat=35.68, lon=139.76, region="東京都"):
    return EarthquakeEvent(event_id="t1", magnitude=mag, depth_km=10.0, latitude=lat, longitude=lon, region=region, timestamp=datetime.now(timezone.utc))

def test_rule_magnitude():
    rule = AlertRule(name="M5+", min_magnitude=5.0)
    assert rule.matches(_event(mag=5.5))
    assert not rule.matches(_event(mag=4.0))

def test_rule_radius():
    rule = AlertRule(name="Tokyo100km", min_magnitude=4.0, center_lat=35.68, center_lon=139.76, radius_km=100)
    assert rule.matches(_event(lat=35.68, lon=139.76))
    assert not rule.matches(_event(lat=40.0, lon=140.0))

def test_rule_region():
    rule = AlertRule(name="Tokyo only", regions=["東京都"])
    assert rule.matches(_event(region="東京都"))
    assert not rule.matches(_event(region="大阪府"))

def test_evaluate_rules():
    rules = [AlertRule(name="big", min_magnitude=6.0), AlertRule(name="any", min_magnitude=3.0)]
    matched = evaluate_rules(_event(mag=5.0), rules)
    assert len(matched) == 1
    assert matched[0]["name"] == "any"
