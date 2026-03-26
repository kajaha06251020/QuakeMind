import pytest
import re
from app.services.paper_survey import _parse_arxiv_atom, search_arxiv_papers

SAMPLE_ATOM = """<?xml version="1.0"?>
<feed><entry>
<title>Earthquake Prediction Using Machine Learning</title>
<summary>We present a novel approach...</summary>
<published>2026-03-25T00:00:00Z</published>
<id>http://arxiv.org/abs/2603.12345</id>
<author><name>A. Researcher</name></author>
</entry></feed>"""


def test_parse_arxiv():
    papers = _parse_arxiv_atom(SAMPLE_ATOM)
    assert len(papers) == 1
    assert "Machine Learning" in papers[0]["title"]
    assert papers[0]["authors"] == ["A. Researcher"]


def test_parse_empty():
    assert _parse_arxiv_atom("<feed></feed>") == []


@pytest.mark.asyncio
async def test_search_disabled(httpx_mock):
    httpx_mock.add_response(url=re.compile(r".*arxiv.*"), text=SAMPLE_ATOM)
    papers = await search_arxiv_papers("test", max_results=1)
    assert len(papers) >= 1
