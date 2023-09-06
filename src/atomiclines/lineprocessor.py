import asyncio
from typing import Callable, TypeAlias

from atomiclines.atomiclinereader import AtomicLineReader, Readable
from atomiclines.backgroundtask import BackgroundTask
from atomiclines.exception import LinesProcessError
from atomiclines.log import logger


class LineHolder:
    """Class passed between the processor function on a LineProcessor.

    Allows either modifying the line, or adding additonal properties.
    """

    def __init__(self, line: bytes) -> None:
        """Init.

        Args:
            line: the initial line
        """
        self.line = line

    def __eq__(self, other: object) -> bool:
        """Comparison function.

        Args:
            other: object to compare against

        Returns:
            true if all instance properties are equal and a subclass of LineHolder
        """
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__

        return False


class LineProcessor(BackgroundTask):
    """Run function(s) for each incomming line."""

    processor_type: TypeAlias = Callable[
        [LineHolder],
        bool | None,  # noqa: WPS465 this is a typehint
    ]

    def __init__(self, streamable: Readable) -> None:
        """Init.

        Args:
            streamable: data stream to monitor for lines.
        """
        self._streamable = streamable
        self._reader = AtomicLineReader(streamable)
        self._processors: list[LineProcessor.processor_type] = []
        super().__init__()

    def start(self) -> None:
        """Start monitioring.

        Whenever possible use the context manager.
        """
        self._reader.start()
        super().start()

    def add_processor(self, processor: processor_type) -> None:
        """Add a callable to process lines.

        Callable will be passed the line as its only argument.
        Callable may return a boolean value, if the callable returns true
        processors registered later will not be presented with the current line.

        Args:
            processor: a callable to process each line with
        """
        self._processors.append(processor)

    def remove_processor(self, processor: processor_type) -> None:
        """Remove a processor (only the first occurance).

        Args:
            processor: processor which is to be removed
        """
        self._processors.remove(processor)

    async def stop(self, timeout: float = 0) -> None:
        """Stop the line processor.

        Prefer the contextmanager whenever possible.

        Args:
            timeout: Time to allow for a graceful shutdown before killing.
                Defaults to 0.
        """
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self._reader.stop(timeout))
            task_group.create_task(super().stop(timeout))

    async def _background_job(self) -> None:
        while not self._background_task_stop:
            try:
                line = await self._reader.readline()
            except LinesProcessError:
                return

            line_object = LineHolder(line)

            for processor in self._processors:
                logger.debug(f"using processor {processor} on {line!r}")

                if processor(line_object):
                    break

            await asyncio.sleep(0)
