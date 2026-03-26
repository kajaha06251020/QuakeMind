from scripts.bulk_import import _parse_fdsn

SAMPLE = """#EventID|Time|Lat|Lon|Depth|...|...|...|...|MagType|Mag|Author|Region
abc123|2026-03-25T10:00:00Z|35.5|139.5|10.0|X|X|X|X|mb|5.2|X|Near Tokyo
"""

def test_parse_fdsn():
    events = _parse_fdsn(SAMPLE, "usgs")
    assert len(events) == 1
    assert events[0]["event_id"] == "usgs-abc123"
    assert events[0]["magnitude"] == 5.2

def test_parse_empty():
    events = _parse_fdsn("#header\n", "usgs")
    assert events == []
