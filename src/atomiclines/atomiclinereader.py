import asyncio
import typing

from atomiclines.backgroundtask import BackgroundTask
from atomiclines.exception import LinesEOFError, LinesProcessError, LinesTimeoutError
from atomiclines.log import logger


class Readable(typing.Protocol):
    """Readable protocol."""

    async def read(self) -> bytes:
        """Read one byte."""


# immitate StreamReader.readuntil
class AtomicLineReader(BackgroundTask):
    """Read lines atomically."""

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
        super().__init__()
        # TODO: allow setting a default timeout

    @property
    def buffer(self) -> bytes:
        """Peek the byte buffer.

        Returns:
            bytes currently held in buffer
        """
        return self._buffer

    async def readline(self, timeout: float | None = None) -> bytes:
        """Read a single line or raise a timeout error.

        Args:
            timeout: timeout in seconds. Defaults to None.

        Raises:
            LinesTimeoutError: if the buffer does not contain an end of line character
                before the timeout expires

        Returns:
            the next line from the buffer (!without the eol character)
        """
        # TODO: should we return a Timeout error or an IncompleteReadError?

        if timeout == 0:
            if self._buffer.find(self._eol) == -1:
                if self.background_task_active:
                    raise LinesTimeoutError(timeout)

                self.raise_for_background_task()
                raise LinesProcessError()  # pragma: no cover the background task on the line before should always raise
                # TODO: asyncio.IncompleteReadError(self._buffer.copy(), None)
        else:
            await self._wait_for_line(timeout)

        line, _, buffer = self._buffer.partition(self._eol)
        self._buffer = buffer

        return line

    def start(self) -> None:
        """Start the background reader process.

        Prefer using this as a context manager whenever you can.
        """
        super().start()
        self.task.add_done_callback(lambda task: self._event_byte_received.set())

    async def stop(self, timeout: float = 0) -> None:
        """Stop reading.

        Args:
            timeout: Timeout for a gracefull shutdown. Defaults to 0.
        """
        self.signal_stop()
        await super().stop(timeout)

    async def _background_job(self) -> None:
        eof_error: LinesEOFError | None = None

        while not self._background_task_stop:
            try:
                bytes_read = await self._streamable.read()
            except LinesEOFError as eof:
                logger.info(f"Got EOF on AtomicLineReader {self._instance_id}.")
                eof_error = eof

                bytes_read = (
                    b""  # ensure that the following code does not assume any bytes read
                )

                if len(self._buffer) and self._buffer[-1:] != self._eol:
                    self._buffer.extend(self._eol)
            else:
                if not len(bytes_read):
                    await asyncio.sleep(0)
                    continue

                self._buffer.extend(bytes_read)

            if self._eol in bytes_read:
                old_data_end = -len(bytes_read)
                line_start = self._buffer.rfind(self._eol, None, old_data_end) + 1
                line_end = self._buffer.find(self._eol, line_start)

                while line_end != -1:
                    logger.info(bytes(self._buffer[line_start:line_end]))
                    line_start = line_end + 1
                    line_end = self._buffer.find(self._eol, line_start)

            self._event_byte_received.set()

            if eof_error is not None:
                await asyncio.sleep(0)
                raise eof_error

    async def _wait_for_line(self, timeout: float | None = None) -> None:
        async with asyncio.timeout(timeout):
            while self._buffer.find(self._eol) == -1:
                if not self.background_task_active:
                    self.raise_for_background_task()

                    raise LinesProcessError()  # In case the background task stopped without raising an exception

                await self._event_byte_received.wait()
                self._event_byte_received.clear()
