"""自動論文サーベイ統合。arXiv から最新の地震研究論文を取得する。"""
import logging
import re
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_ARXIV_API = "http://export.arxiv.org/api/query"


async def search_arxiv_papers(
    query: str = "earthquake prediction seismology",
    max_results: int = 10,
) -> list[dict]:
    """arXiv API で地震研究論文を検索する。"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_ARXIV_API, params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            })
            resp.raise_for_status()
            return _parse_arxiv_atom(resp.text)
    except Exception as e:
        logger.error("[PaperSurvey] arXiv API エラー: %s", e)
        return []


def _parse_arxiv_atom(xml_text: str) -> list[dict]:
    """arXiv Atom XML をパースする。"""
    papers = []
    entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)

    for entry in entries:
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        published = re.search(r"<published>(.*?)</published>", entry)
        arxiv_id = re.search(r"<id>(.*?)</id>", entry)
        authors = re.findall(r"<name>(.*?)</name>", entry)

        if not title:
            continue

        papers.append({
            "title": title.group(1).strip().replace("\n", " "),
            "summary": summary.group(1).strip().replace("\n", " ")[:500] if summary else "",
            "published": published.group(1) if published else "",
            "arxiv_url": arxiv_id.group(1) if arxiv_id else "",
            "authors": authors[:5],
        })

    return papers


async def survey_latest_research(topics: list[str] | None = None) -> dict:
    """複数トピックの最新論文をサーベイする。"""
    if topics is None:
        topics = [
            "earthquake forecasting ETAS",
            "seismicity rate change detection",
            "Coulomb stress earthquake triggering",
            "machine learning earthquake prediction",
            "b-value temporal variation",
        ]

    all_papers = {}
    for topic in topics:
        papers = await search_arxiv_papers(topic, max_results=3)
        all_papers[topic] = papers

    total = sum(len(p) for p in all_papers.values())
    return {
        "surveyed_at": datetime.now(timezone.utc).isoformat(),
        "n_topics": len(topics),
        "total_papers": total,
        "topics": all_papers,
    }
