import asyncio
import logging
from typing import Any, Coroutine

from tester.atomiclinereader import AtomicLineReader
from tester.backgroundtask import BackgroundTask

logging.getLogger().addHandler(logging.StreamHandler())
logging.getLogger().setLevel(logging.NOTSET)


class LineProcessor(BackgroundTask):
    def __init__(self, streamable) -> None:
        self._streamable = streamable
        self._reader = AtomicLineReader(streamable)
        self._processors = []
        super().__init__()

    def start(self) -> None:
        self._reader.start()
        super().start()

    def add_processor(self, processor):
        self._processors.append(processor)

    def remove_processor(self, processor):
        self._processors.remove(processor)

    async def stop(self, timeout: float = 0) -> Coroutine[Any, Any, None]:
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self._reader.stop(timeout))
            task_group.create_task(super().stop(timeout))

    async def _background_job(self) -> None:
        while self._background_task_active:
            try:
                line = await self._reader.readline()
            except RuntimeError:
                return

            for processor in self._processors:
                # TODO: log? print(f"using processor {processor} on {line}")
                processor(line)

            await asyncio.sleep(0)
