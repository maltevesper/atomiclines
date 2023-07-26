import asyncio
import contextlib
import logging
import typing

logging.getLogger("tester.atomiclinereader")


class Readable(typing.Protocol):
    """Readable protocol."""

    def read(self) -> bytes:
        """Read one byte."""


# immitate StreamReader.readuntil
class AtomicLineReader:
    """Read lines atomically."""

    # TODO: type annotations explicit?
    _reader_task: asyncio.Task
    _reader_active: bool
    _eol: bytes
    _instances: int = 0

    def __init__(self, streamable: Readable) -> None:
        """Generate a reader.

        Args:
            streamable: object which provides an async read method, returning one byte
        """
        self._buffer = bytearray()  # TODO ringbuffer, that exposes a memoryview
        self._event_byte_received = asyncio.Event()
        self._streamable = streamable
        self._reader_active = False
        self._eol = b"\n"
        self._instance_id = self._instances
        AtomicLineReader._instances += 1  # noqa: WPS437 - "private" access is intended
        self._logger = logging.getLogger(
            f"tester.atomiclinereader.instance{self._instance_id}",
        )
        self._logger.setLevel(logging.INFO)

        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(
            logging.Formatter(fmt="{asctime}: {message}", style="{"),
        )

        self._logger.addHandler(stderr_handler)

        self.start_reader()
        # TODO: allow setting a default timeout

    @property
    def buffer(self) -> bytes:
        """Peek the byte buffer.

        Returns:
            bytes currently held in buffer
        """
        return self._buffer

    def start_reader(self) -> None:
        """Start the reader coroutine."""
        # if self._reader_task is None or self._reader_task.done():
        if not self._reader_active:
            self._logger.debug(
                f"Starting reader for AtomicLineReader {self._instance_id}",
            )
            self._reader_active = True
            self._reader_task = asyncio.create_task(self._reader())
            self._reader_task.add_done_callback(
                lambda task: self._reader_exit_check(task),
            )

    async def stop_reader(self, timeout: float = 0) -> None:
        """Stop the reader coroutine.

        Args:
            timeout: timeout in seconds before the reader process is forcefully
                cancelled.
        """
        self._logger.debug(
            f"Stopping reader for AtomicLineReader {self._instance_id}",
        )
        self._reader_active = False

        await asyncio.sleep(timeout)  # allow reader coroutine to schedule and finish
        self._reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(self._reader_task, 1)

    async def __aenter__(self):
        """Asynchronous context manager, which starts the reader.

        Returns:
            AtomicLineReader instance
        """
        self.start_reader()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Close the asynchronous context manager and stop the reader."""
        # TODO: should we only stop the reader if we started it?
        await self.stop_reader()

    async def readline(self, timeout: float | None = None) -> bytes:
        """Read a single line or raise a timeout error.

        Args:
            timeout: timeout in seconds. Defaults to None.

        Raises:
            TimeoutError: if the buffer does not contain an end of line character
                before the timeout expires

        Returns:
            the next line from the buffer (!without the eol character)
        """
        # TODO: should we return a Timeout error or an IncompleteReadError?

        if timeout == 0:
            if self._buffer.find(self._eol) == -1:
                raise TimeoutError()  # TODO custom timeout error with information about the timeout
                # raise asyncio.IncompleteReadError(
                #         self._buffer.copy(),
                #         None,
                #     )  # TODO: custom exception subclassing asyncio.IncompleteReadError
        else:
            async with asyncio.timeout(timeout):
                while self._buffer.find(self._eol) == -1:
                    await self._event_byte_received.wait()
                    self._event_byte_received.clear()

        line, _, buffer = self._buffer.partition(self._eol)
        self._buffer = buffer

        return line

    async def _reader(self) -> None:
        while self._reader_active:
            # TODO: optimize read one byte or all available bytes
            bytes_read = await self._streamable.read()

            if bytes_read == self._eol:
                line_start = self._buffer.rfind(self._eol) + 1
                self._logger.info(self._buffer[line_start:])

            self._buffer.extend(bytes_read)
            self._event_byte_received.set()

    def _reader_exit_check(self, task: asyncio.Task):
        self._reader_active = False

        with contextlib.suppress(asyncio.CancelledError):
            if task.exception() is not None:
                self._logger.error(
                    f"An error occured in the reader process. {task.exception()}",
                )
        # TODO limit restart attempts based on time to last crash and number of attempts
        # if self._reader_active:
        #     self.start_reader()
