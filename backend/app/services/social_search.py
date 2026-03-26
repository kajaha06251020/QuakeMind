"""ソーシャルメディア地震体感検索。

Yahoo! リアルタイム検索（スクレイピング回避のため検索URL生成のみ）と
Mastodon public timeline 検索。
"""
import logging
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)

_MASTODON_INSTANCES = [
    "https://mastodon.social",
    "https://mstdn.jp",
]

_SEARCH_KEYWORDS = ["地震", "揺れた", "earthquake"]


async def search_mastodon(keyword: str = "地震", limit: int = 20) -> list[dict]:
    """Mastodon パブリックタイムラインから地震関連投稿を検索する。"""
    results = []
    for instance in _MASTODON_INSTANCES:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{instance}/api/v1/timelines/public",
                    params={"limit": limit, "local": False},
                )
                resp.raise_for_status()
                posts = resp.json()
                for post in posts:
                    content = post.get("content", "")
                    if any(kw in content for kw in _SEARCH_KEYWORDS):
                        results.append({
                            "source": "mastodon",
                            "instance": instance,
                            "content": content[:300],
                            "created_at": post.get("created_at", ""),
                            "url": post.get("url", ""),
                            "account": post.get("account", {}).get("acct", ""),
                        })
        except Exception as e:
            logger.warning("[Social] Mastodon %s エラー: %s", instance, e)
            continue
    return results[:limit]


def generate_yahoo_search_url(keyword: str = "地震") -> str:
    """Yahoo! リアルタイム検索の URL を生成する（API なし、URL 生成のみ）。"""
    from urllib.parse import quote
    return f"https://search.yahoo.co.jp/realtime/search?p={quote(keyword)}"


async def search_social(keyword: str = "地震", limit: int = 20) -> dict:
    """全ソーシャルソースを統合検索する。"""
    mastodon_results = await search_mastodon(keyword, limit)
    return {
        "keyword": keyword,
        "mastodon": mastodon_results,
        "yahoo_search_url": generate_yahoo_search_url(keyword),
        "total_posts": len(mastodon_results),
    }
