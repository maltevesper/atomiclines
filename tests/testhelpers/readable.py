"""Mock readables."""
import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import NoReturn

from atomiclines.exception import LinesEOFError


class MockReadable:
    """A mock readable returning data from a generator."""

    def __init__(self, data_stream: AsyncGenerator[bytes, None]) -> None:
        """Initialize mock readable.

        Return data from genereator, block eternally once the generator is exhausted.

        Args:
            data_stream: generator generating the data to be returned on read() calls.
        """
        self._data_stream = data_stream

    async def read(self) -> bytes:
        """Return next available byte from generator.

        Returns:
            bytes yielded by generator.
        """
        with suppress(StopAsyncIteration):
            return await anext(self._data_stream)

        await asyncio.Future()  # run forever
        return b""  # dummy return, never reached


class ExceptionalReadable:
    """A readable which throws an exception on read."""

    async def read(self) -> NoReturn:
        """Read implementation.

        Raises:
            RuntimeError: every time
        """
        raise RuntimeError


class EOFReadable:
    """A readable which raises EOF at the end."""

    def __init__(self, data_stream: AsyncGenerator[bytes, None]) -> None:
        """Initialize EOFReadable.

        Args:
            data_stream: generator generating the data to be returned on read() calls.
        """
        self._data_stream = data_stream

    async def read(self) -> bytes:
        """Read byte.

        Raises:
            LinesEOFError: EOF reached

        Returns:
            byte read
        """
        try:
            return await anext(self._data_stream)
        except StopAsyncIteration:
            raise LinesEOFError from None
