"""バックグラウンドジョブ管理。

asyncio ベースのシンプルなジョブスケジューラー。
Celery/ARQ は将来的に導入する前提で、インターフェースを合わせる。
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class Job:
    def __init__(self, name: str, func: Callable[..., Awaitable], interval_seconds: int):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.last_run: datetime | None = None
        self.run_count: int = 0
        self.error_count: int = 0
        self.last_error: str | None = None
        self._task: asyncio.Task | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "is_running": self._task is not None and not self._task.done(),
        }


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def register(self, name: str, func: Callable[..., Awaitable], interval_seconds: int) -> None:
        self._jobs[name] = Job(name, func, interval_seconds)

    async def _run_job_loop(self, job: Job) -> None:
        while True:
            try:
                await job.func()
                job.last_run = datetime.now(timezone.utc)
                job.run_count += 1
                logger.debug("[JobManager] %s 完了 (#%d)", job.name, job.run_count)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                job.error_count += 1
                job.last_error = str(e)
                logger.error("[JobManager] %s エラー: %s", job.name, e)
            await asyncio.sleep(job.interval_seconds)

    def start_all(self) -> list[asyncio.Task]:
        tasks = []
        for job in self._jobs.values():
            job._task = asyncio.create_task(self._run_job_loop(job))
            tasks.append(job._task)
            logger.info("[JobManager] %s 開始 (間隔: %ds)", job.name, job.interval_seconds)
        return tasks

    def stop_all(self) -> None:
        for job in self._jobs.values():
            if job._task and not job._task.done():
                job._task.cancel()

    def get_status(self) -> dict:
        return {
            "jobs": {name: job.to_dict() for name, job in self._jobs.items()},
            "total_jobs": len(self._jobs),
        }


# グローバルインスタンス
job_manager = JobManager()
