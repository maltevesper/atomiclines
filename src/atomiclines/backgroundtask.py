import asyncio
import contextlib
import traceback
from types import TracebackType
from typing import Any, Protocol, Self, Type

from atomiclines.exception import LinesTimeoutError
from atomiclines.log import logger


class Readable(Protocol):
    """Readable protocol."""

    def read(self) -> bytes:
        """Read one byte."""


class DoneTask(asyncio.Future):
    """A Future which has completed."""

    def __init__(self, future_result: Any = None) -> None:
        """Initialize completed Future.

        Args:
            future_result: Future return value. Defaults to None.
        """
        super().__init__()
        self.set_result(future_result)


# immitate StreamReader.readuntil
class BackgroundTask:
    """Read lines atomically."""

    _background_task: asyncio.Task | asyncio.Future

    def __init__(self) -> None:
        """Generate a reader."""
        self._background_task = DoneTask()

    @property
    def background_task_active(self) -> bool:
        """Check if the background task is (still) running.

        Returns:
            bool indication if the background task is running.
        """
        return not self._background_task.done()

    def raise_for_background_task(self):
        """Raise the exception raised by the background task.

        Raises:
            exception: the exception raised by the
                background task
        """
        if self._background_task.exception():
            raise self._background_task.exception()

    def start(self) -> None:
        """Start the reader coroutine."""
        if not self.background_task_active:
            logger.debug(
                f"Starting  background task for {super()!r}",
            )
            self._background_task_stop = False
            self._background_task = asyncio.create_task(self._background_job())
            self._background_task.add_done_callback(
                lambda task: self._job_exit_check(task),
            )

    def signal_stop(self) -> None:
        """Request a soft stop of the background thread."""
        logger.debug(
            f"Signaling stop to background task for {super()!r}",
        )
        self._background_task_stop = True

    async def stop(self, timeout: float = 0) -> None:
        """Stop the reader coroutine.

        Raises any errors which might have occured in the background task.

        Raises:
            LinesTimeoutError: timeout occured

        Args:
            timeout: timeout in seconds before the reader process is forcefully
                cancelled.
        """
        logger.debug(
            f"Starting  background task for {super()!r}",
        )
        self.signal_stop()

        if timeout == 0:
            self._background_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.wait_for(self._background_task, 0.1)
            return

        try:
            await asyncio.wait_for(self._background_task, timeout)
        except TimeoutError as timeout_exception:
            logger.debug(
                f"Cancelled background task for {super()!r} after {timeout} "
                + "second timeout.",
            )

            self._background_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.wait_for(self._background_task, 0.1)

            raise LinesTimeoutError(timeout) from timeout_exception

    @property
    def task(self) -> asyncio.Future:
        """Get the background task.

        Usefull for adding done callbacks (add_done_callback).

        Returns:
            the background task object
        """
        return self._background_task

    async def __aenter__(self) -> Self:
        """Asynchronous context manager, which starts the reader.

        Returns:
            AtomicLineReader instance
        """
        self.start()
        return self

    async def __aexit__(
        self,
        _exc_type: Type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Close the asynchronous context manager and stop the reader."""
        await self.stop()

    # @abstractmethod
    async def _background_job(self) -> None:
        """Function to run in the background (as an Asyncio task).

        A typical implemntation should check on self._background_task_stop,
        since this is used to signal a soft stop.

        while not self._background_task_stop:
            doSomething()

        Raises:
            NotImplementedError: _description_
        """  # noqa: D401
        raise NotImplementedError

    def _job_exit_check(self, task: asyncio.Task) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            if task.exception() is not None:
                logger.error(
                    f"An error occured in the background process. {task.exception()}",
                )
                logger.error(traceback.format_exception(task.exception()))
                # exception will be raise when task is awaited, no need to raise here

        # TODO limit restart attempts based on time to last crash and number of attempts
        # iff self._reader_active: self.start_reader()
