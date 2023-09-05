import asyncio
import time
from typing import Any, Coroutine

import pytest

from atomiclines.backgroundtask import BackgroundTask
from atomiclines.exception import LinesTimeoutError


class UncooperativeBackgroundJob(BackgroundTask):
    async def _background_job(self) -> Coroutine[Any, Any, None]:
        while True:
            time.sleep(0.1)
            await asyncio.sleep(0)


async def test_repeated_start():
    background_job = UncooperativeBackgroundJob()
    async with background_job:
        background_job.start()

    # TODO: what to we assert here?


async def test_stop_timeout():
    background_job = UncooperativeBackgroundJob()
    async with background_job:
        with pytest.raises(LinesTimeoutError):
            await background_job.stop(0.01)
