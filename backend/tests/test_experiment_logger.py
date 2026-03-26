import pytest
from app.services.experiment_logger import log_experiment, get_experiment_logs, track_experiment

@pytest.mark.asyncio
async def test_log_and_get(db_engine):
    await log_experiment("test_exp", {"param": 1}, {"accuracy": 0.95}, 1.5)
    logs = await get_experiment_logs()
    assert len(logs) >= 1
    assert logs[0]["experiment_name"] == "test_exp"

@pytest.mark.asyncio
async def test_track_experiment(db_engine):
    async with track_experiment("tracked", {"x": 1}) as exp:
        exp["results"] = {"value": 42}
    logs = await get_experiment_logs(name="tracked")
    assert len(logs) >= 1
    assert logs[0]["results"]["value"] == 42
    assert logs[0]["duration_seconds"] is not None

@pytest.mark.asyncio
async def test_filter_by_name(db_engine):
    await log_experiment("exp_a", {}, {})
    await log_experiment("exp_b", {}, {})
    logs = await get_experiment_logs(name="exp_a")
    assert all(l["experiment_name"] == "exp_a" for l in logs)
