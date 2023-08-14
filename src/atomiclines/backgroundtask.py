import asyncio
import contextlib
import traceback
import typing

from atomiclines.exception import LinesTimeoutError
from atomiclines.log import logger


class Readable(typing.Protocol):
    """Readable protocol."""

    def read(self) -> bytes:
        """Read one byte."""


# immitate StreamReader.readuntil
class BackgroundTask:
    """Read lines atomically."""

    _background_task: asyncio.Task
    _background_task_active: bool

    def __init__(self) -> None:
        """Generate a reader."""
        self._background_task_active = False
        # TODO: allow setting a default timeout

    def start(self) -> None:
        """Start the reader coroutine."""
        # if self._reader_task is None or self._reader_task.done():
        if not self._background_task_active:
            logger.debug(
                f"Starting  background task for {super()!r}",
            )
            self._background_task_active = True
            self._background_task = asyncio.create_task(self._background_job())
            self._background_task.add_done_callback(
                lambda task: self._job_exit_check(task),
            )

    def signal_stop(self) -> None:
        """Request a soft stop of the background thread."""
        logger.debug(
            f"Signaling stop to background task for {super()!r}",
        )
        self._background_task_active = False

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
            raise LinesTimeoutError(timeout) from timeout_exception

    async def __aenter__(self):
        """Asynchronous context manager, which starts the reader.

        Returns:
            AtomicLineReader instance
        """
        self.start()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Close the asynchronous context manager and stop the reader."""
        # TODO: should we only stop the reader if we started it?
        await self.stop()

    # @abstractmethod
    async def _background_job(self) -> None:
        """Function to run in the background (as an Asyncio task).

        A typical implemntation should check on self._background_task_active,
        since this is used to signal a soft stop.

        while self._background_task_active:
            doSomething()

        Raises:
            NotImplementedError: _description_
        """  # noqa: D401
        raise NotImplementedError

    def _job_exit_check(self, task: asyncio.Task):
        self._background_task_active = False

        with contextlib.suppress(asyncio.CancelledError):
            if task.exception() is not None:
                logger.error(
                    f"An error occured in the background process. {task.exception()}",
                )
                logger.error(traceback.format_exception(task.exception()))
                # exception will be raise when task is awaited, no need to raise here

        # TODO limit restart attempts based on time to last crash and number of attempts
        # iff self._reader_active: self.start_reader()
