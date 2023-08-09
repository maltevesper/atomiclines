import asyncio
import logging
import typing
from typing import Any, Coroutine

from tester.backgroundtask import BackgroundTask

logging.getLogger("tester.atomiclinereader")


class Readable(typing.Protocol):
    """Readable protocol."""

    def read(self) -> bytes:
        """Read one byte."""


# immitate StreamReader.readuntil
class AtomicLineReader(BackgroundTask):
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
        # self._reader_active = False
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

        super().__init__(self._logger)
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
            TimeoutError: if the buffer does not contain an end of line character
                before the timeout expires

        Returns:
            the next line from the buffer (!without the eol character)
        """
        # TODO: should we return a Timeout error or an IncompleteReadError?
        # TODO: should a readline call be cancelable? I.e. if the reader is stopped, how should readline behave?
        #     -> a) cancel hard immediately <= simpler, least surprise
        #     -> b) if Timeout is none cancel hard immediately

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

                    if not self._background_task_active:
                        raise RuntimeError()  # TODO more appropiate exception, if the reader gets cancelled.

        line, _, buffer = self._buffer.partition(self._eol)
        self._buffer = buffer

        return line

    async def stop(self, timeout: float = 0) -> Coroutine[Any, Any, None]:
        self.signal_stop()
        self._event_byte_received.set()  # TODO: the donecallback should do this, so a crash is handled too
        await super().stop(timeout)

    async def _background_job(self) -> None:
        while self._background_task_active:
            # TODO: optimize read one byte or all available bytes
            bytes_read = await self._streamable.read()

            if bytes_read == self._eol:
                line_start = self._buffer.rfind(self._eol) + 1
                self._logger.info(self._buffer[line_start:])

            self._buffer.extend(bytes_read)
            self._event_byte_received.set()
