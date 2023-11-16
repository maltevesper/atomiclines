"""Test BackgroundTask implementation."""
import asyncio
import time
from collections.abc import Coroutine
from typing import Any

import pytest
from atomiclines.backgroundtask import BackgroundTask
from atomiclines.exception import LinesTimeoutError


class UncooperativeBackgroundJob(BackgroundTask):
    """BackgroundTask which does not honor the stop signal."""

    async def _background_job(self) -> Coroutine[Any, Any, None]:
        """BackgroundJob implementation which ignores the stop signal."""
        while True:
            time.sleep(0.1)  # noqa: ASYNC101 for test purposes we simulate compute
            # heavy workload with sleep
            await asyncio.sleep(0)


async def test_repeated_start() -> None:
    """Test starting the same background job multiple times."""
    background_job = UncooperativeBackgroundJob()
    async with background_job:
        background_job.start()

    # TODO: what to we assert here?


async def test_stop_timeout() -> None:
    """Make sure timeout is honored by stop."""
    background_job = UncooperativeBackgroundJob()
    async with background_job:
        with pytest.raises(LinesTimeoutError):
            await background_job.stop(0.01)
