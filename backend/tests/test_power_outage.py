from app.services.power_outage import get_power_outage_urls


def test_power_urls_all():
    result = get_power_outage_urls()
    assert len(result["companies"]) == 5


def test_power_urls_tokyo():
    result = get_power_outage_urls("東京都")
    assert "tepco" in result["companies"]


def test_power_urls_osaka():
    result = get_power_outage_urls("大阪府")
    assert "kepco" in result["companies"]
