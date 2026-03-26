import asyncio
import pytest
from app.services.job_manager import JobManager


@pytest.mark.asyncio
async def test_job_registration():
    mgr = JobManager()
    mgr.register("test", lambda: asyncio.sleep(0), 60)
    status = mgr.get_status()
    assert status["total_jobs"] == 1
    assert "test" in status["jobs"]


@pytest.mark.asyncio
async def test_job_status_fields():
    mgr = JobManager()
    mgr.register("test", lambda: asyncio.sleep(0), 60)
    job_info = mgr.get_status()["jobs"]["test"]
    assert job_info["name"] == "test"
    assert job_info["run_count"] == 0
    assert job_info["is_running"] is False
