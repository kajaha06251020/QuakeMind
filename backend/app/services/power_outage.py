"""停電情報サービス。

東京電力等の停電情報を取得する。
実際のAPIは各電力会社で異なるため、構造化されたスタブ + TEPCO サイトURL生成。
"""
import logging

logger = logging.getLogger(__name__)

# 電力会社の停電情報ページ
_POWER_COMPANIES = {
    "tepco": {"name": "東京電力", "url": "https://teideninfo.tepco.co.jp/"},
    "kepco": {"name": "関西電力", "url": "https://www.kansai-td.co.jp/teideninfo/"},
    "chubu": {"name": "中部電力", "url": "https://teiden.powergrid.chuden.co.jp/"},
    "tohoku": {"name": "東北電力", "url": "https://nw.tohoku-epco.co.jp/teideninfo/"},
    "kyushu": {"name": "九州電力", "url": "https://www.kyuden.co.jp/td_top_map_fr.html"},
}


def get_power_outage_urls(region: str | None = None) -> dict:
    """停電情報確認用の URL リストを返す。"""
    if region:
        matched = {}
        if "東京" in region or "関東" in region or "神奈川" in region or "千葉" in region or "埼玉" in region:
            matched["tepco"] = _POWER_COMPANIES["tepco"]
        if "大阪" in region or "京都" in region or "兵庫" in region or "関西" in region:
            matched["kepco"] = _POWER_COMPANIES["kepco"]
        if "名古屋" in region or "愛知" in region or "中部" in region:
            matched["chubu"] = _POWER_COMPANIES["chubu"]
        if "仙台" in region or "宮城" in region or "東北" in region:
            matched["tohoku"] = _POWER_COMPANIES["tohoku"]
        if "福岡" in region or "九州" in region:
            matched["kyushu"] = _POWER_COMPANIES["kyushu"]
        if not matched:
            matched = _POWER_COMPANIES  # マッチしなければ全部返す
        return {"region": region, "companies": matched}

    return {"region": None, "companies": _POWER_COMPANIES}
