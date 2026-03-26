import pytest
from app.services.research_journal import add_entry, get_entries

@pytest.mark.asyncio
async def test_add_and_get(db_engine):
    entry_id = await add_entry("finding", "b値低下を検出", "東京都でb値が0.85に低下", region="東京都")
    assert entry_id is not None
    entries, total = await get_entries()
    assert total >= 1
    assert entries[0]["title"] == "b値低下を検出"

@pytest.mark.asyncio
async def test_filter_by_type(db_engine):
    await add_entry("finding", "Finding 1", "content")
    await add_entry("anomaly", "Anomaly 1", "content")
    entries, total = await get_entries(entry_type="anomaly")
    assert all(e["entry_type"] == "anomaly" for e in entries)

@pytest.mark.asyncio
async def test_empty(db_engine):
    entries, total = await get_entries()
    assert total == 0
