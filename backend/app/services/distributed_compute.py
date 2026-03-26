"""分散計算フレームワーク。asyncio + concurrent.futures でCPUバウンド計算を並列化。"""
import asyncio, logging, time
from concurrent.futures import ProcessPoolExecutor
logger = logging.getLogger(__name__)

_executor = None

def get_executor(max_workers: int = 4) -> ProcessPoolExecutor:
    global _executor
    if _executor is None: _executor = ProcessPoolExecutor(max_workers=max_workers)
    return _executor

async def run_parallel(func, args_list: list, max_workers: int = 4) -> list:
    """関数を複数の引数セットで並列実行する。"""
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, func, *args) for args in args_list]
    return await asyncio.gather(*tasks, return_exceptions=True)

def compute_stats() -> dict:
    return {"executor_active": _executor is not None, "description": "asyncio + ProcessPoolExecutor ベースの分散計算"}
