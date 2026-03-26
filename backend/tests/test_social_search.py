import re
import pytest
from app.services.social_search import generate_yahoo_search_url, search_social

_MASTODON_SOCIAL_PATTERN = re.compile(r"https://mastodon\.social/api/v1/timelines/public.*")
_MSTDN_JP_PATTERN = re.compile(r"https://mstdn\.jp/api/v1/timelines/public.*")


def test_yahoo_url():
    url = generate_yahoo_search_url("地震")
    assert "search.yahoo.co.jp/realtime" in url
    assert "%E5%9C%B0%E9%9C%87" in url  # URL encoded 地震


@pytest.mark.asyncio
async def test_search_social_returns_structure(httpx_mock):
    # Mock mastodon to return empty (no real HTTP)
    httpx_mock.add_response(url=_MASTODON_SOCIAL_PATTERN, json=[])
    httpx_mock.add_response(url=_MSTDN_JP_PATTERN, json=[])
    result = await search_social("地震")
    assert "mastodon" in result
    assert "yahoo_search_url" in result
    assert "total_posts" in result
