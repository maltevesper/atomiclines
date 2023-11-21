"""Process each line received with multiple functions."""
import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import Self, TypeAlias

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

    def __str__(self) -> str:
        """Generate string representation.

        Returns:
            String representation
        """
        return self.line.decode()

    def __repr__(self) -> str:
        """Representation.

        Returns:
            programmatic representation.
        """
        return f"<LineHolder({self.line.decode()})>"


class LineProcessor(BackgroundTask):
    """Run function(s) for each incomming line."""

    ProcessorType: TypeAlias = Callable[
        [LineHolder],
        Awaitable[bool | None],
    ]

    def __init__(self, streamable: Readable) -> None:
        """Init.

        Args:
            streamable: data stream to monitor for lines.
        """
        self._streamable = streamable
        self._reader = AtomicLineReader(streamable)
        self._processors: list[LineProcessor.ProcessorType] = []
        super().__init__()

    def start(self) -> None:
        """Start monitioring.

        Whenever possible use the context manager.
        """
        self._reader.start()
        super().start()

    @property
    def processors(self) -> list[ProcessorType]:
        """Return the list of processors.

        Returns:
            list of processors to be used
        """
        return self._processors

    @contextmanager
    def temporary_processor(
        self,
        temporary_processors: ProcessorType | list[ProcessorType],
        index: int | None = 0,
    ) -> Iterator[Self]:
        """Contextmanager to temporarily attach a processor.

        Args:
            temporary_processors: processor to attach temporarily
            index: Position into which the processor is inserted.
                   Defaults to 0 (first processor). Use None to append.

        Yields:
            self
        """
        original_processors = self._processors.copy()

        self.add_processor(temporary_processors, index)

        try:
            yield self
        finally:
            self._processors = original_processors

    def add_processor(
        self,
        processors: ProcessorType | list[ProcessorType],
        index: int | None = None,
    ) -> ProcessorType:
        """Add a callable to process lines.

        Callable will be passed the line as its only argument.
        Callable may return a boolean value, if the callable returns true
        processors registered later will not be presented with the current line.

        Args:
            processors: a callable to process each line with
            index: position into which to insert processors (None = end)

        Returns:
            the async lineprocessor
        """
        # `always_iterable(processors))` fails with AsyncMock which is considered
        # iterable...
        if not isinstance(processors, list):
            processors = [processors]

        for processor in processors:
            if isinstance(processor, LineProcessingFuncBase):
                processor.init_lineprocessor(self)

        if index is None:
            index = len(self._processors)

        self._processors[index:index] = processors

        return processors

    def remove_processor(self, processor: ProcessorType) -> None:
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
            except LinesProcessError:  # TODO: is this sensible handling?
                return

            line_object = LineHolder(line)

            for processor in self._processors.copy():
                logger.debug(f"using processor {processor} on {line!r}")

                if await processor(line_object):
                    break

            await asyncio.sleep(0)


def wrap_as_async(
    processor: Callable[[LineHolder], bool | None],
) -> LineProcessor.ProcessorType:
    """Decorator wrap a sync processor into an async function.

    Args:
        processor: processor to wrap

    Returns:
        Async wrapper of processor
    """

    @wraps(processor)
    async def async_processor(lineholder: LineHolder) -> bool | None:
        return processor(lineholder)

    return async_processor


class LineProcessingFuncBase(ABC):
    """Base Class for Callable object processor function for LineProcessor.

    Provides a back reference to the LineProcessor in the `lineprocessor` property.
    DO not add the same instance to different LineProcessors.
    """

    def __init__(self) -> None:
        """Initialization."""
        self._lineprocessor: LineProcessor | None = (
            None  # TODO: should we call this parent or something else?
        )

    def init_lineprocessor(self, line_processor: LineProcessor) -> None:
        """Bind to lineprocessor.

        Args:
            line_processor: LineProcessor to bind to.

        Raises:
            RuntimeError: LineProcessingFuncBase can not be bound to multiple instances,
                thus binding more than once is disallowed.
        """
        if self._lineprocessor is not None:
            message = (
                f"{self} is already bound to LineProcessor {self._lineprocessor}. "
                f"Can't rebind to {line_processor}.\n"
                "Do not reuse LineProcessingFuncBase instances."
            )
            raise RuntimeError(message)

        self._lineprocessor = line_processor

    @property
    def lineprocessor(self) -> LineProcessor:
        """Get the LineProcessor the LineProcessing function is attached too.

        Raises:
            RuntimeError: When the property is accessed before the LineProcessor
                initialized it (during the addProcessor call)

        Returns:
            the parent LineProcessor object the processor is assigned to.
        """
        if self._lineprocessor is None:
            message = "Backreference self._lineprocessor was never initialized."
            raise RuntimeError(  # TODO: custom exception
                message,
            )

        return self._lineprocessor

    @abstractmethod
    async def __call__(self, line_holder: LineHolder) -> bool | None:
        """Implement actual lineprocessing.

        Args:
            line_holder: line to be processed

        Raises:
            NotImplementedError: this is an abstract method

        Returns:
            boolean / None, True if line should not be processed by any
            subsequent processors.
        """
        raise NotImplementedError
