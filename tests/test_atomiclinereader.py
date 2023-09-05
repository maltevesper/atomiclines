import asyncio
import contextlib
import io
import typing
from logging import INFO

import pytest

from atomiclines.atomiclinereader import AtomicLineReader
from atomiclines.exception import LinesProcessError, LinesTimeoutError
from atomiclines.log import logger


async def bytestream_equal_spacing(bytesequence: bytes, interval_s: float = 0):
    """Return bytes from bytesequence and add delay between.

    Args:
        bytesequence: byte sequence to yeild from
        interval_s: delay between bytes. Defaults to 0.

    Yields:
        single bytes from bytesequence.
    """
    for byte in bytesequence:
        yield bytes([byte])
        await asyncio.sleep(interval_s)


async def multibytestream_equal_spacing(bytesequence: bytes, interval_s: float = 0):
    """Return bytes from bytesequence and add delay between.

    Args:
        bytesequence: byte sequence to yeild from
        interval_s: delay between bytes. Defaults to 0.

    Yields:
        single bytes from bytesequence.
    """
    byteiter = iter(bytesequence)

    for byte_chunk in zip(byteiter, byteiter):
        yield bytes(byte_chunk)
        await asyncio.sleep(interval_s)


async def bytestream_zero_delay(bytesequence: bytes):
    """Return single bytes from a bytes object.

    Args:
        bytesequence: bytesequence to iterate over

    Yields:
        single bytes from bytesequence
    """
    for byte in bytesequence:
        yield bytes([byte])


class MockReadable:
    """A mock readable returning data from a generator."""

    def __init__(self, data_stream: typing.AsyncGenerator[bytes, None]) -> None:
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
        with contextlib.suppress(StopAsyncIteration):
            return await anext(self._data_stream)

        await asyncio.Future()  # run forever


class ExceptionalReadable:
    """A readable which throws an exception on read."""

    async def read(self):
        """Read implementation.

        Raises:
            RuntimeError: every time
        """
        raise RuntimeError


async def test_readline():
    """Test readline with a timeout > 0."""
    # with pytest.raises(TimeoutError):
    bytestream = b"hello\nworld\n."
    bytesreader = io.BytesIO(bytestream)

    async with AtomicLineReader(
        MockReadable(bytestream_equal_spacing(bytestream, 0)),
    ) as atomic_reader:
        assert bytesreader.readline().strip() == await atomic_reader.readline(0.1)
        assert bytesreader.readline().strip() == await atomic_reader.readline(0.1)

        with pytest.raises(TimeoutError):
            await atomic_reader.readline(0.1)


async def test_readline_multibyte(caplog: pytest.LogCaptureFixture):
    """Test readline with a timeout > 0."""
    bytestream = b"hello\nworld\n\n\n."
    bytesreader = io.BytesIO(bytestream)

    with caplog.at_level(INFO, logger.name):
        async with AtomicLineReader(
            MockReadable(multibytestream_equal_spacing(bytestream, 0.01)),
        ) as atomic_reader:
            assert bytesreader.readline().strip() == await atomic_reader.readline(0.1)
            assert bytesreader.readline().strip() == await atomic_reader.readline(0.1)
            await asyncio.sleep(0.1)

    assert caplog.messages == list(map(str, bytestream.split(b"\n")[:-1]))


async def test_readline_fastpath():
    """Make sure readline with timeout 0 works."""
    bytestream = b"hello\nworld\n."
    bytesreader = io.BytesIO(bytestream)

    async with AtomicLineReader(
        MockReadable(bytestream_zero_delay(bytestream)),
    ) as atomic_reader:
        await asyncio.sleep(0)  # allow reader process to fill buffer
        assert bytesreader.readline().strip() == await atomic_reader.readline(0)
        assert bytesreader.readline().strip() == await atomic_reader.readline(0)

        with pytest.raises(LinesTimeoutError):
            await atomic_reader.readline(0)


async def test_stopreader_hardstop():
    """Stop the reader process by injecting a CancelledError."""
    atomic_reader = AtomicLineReader(
        MockReadable(bytestream_equal_spacing(b"hello", 0.5)),
    )

    async with atomic_reader:
        await asyncio.sleep(0)

    assert atomic_reader.buffer == b"h"


async def test_stopreader_softstop():
    """Stop reader without injeciting a CancelledError."""
    atomic_reader = AtomicLineReader(
        MockReadable(bytestream_equal_spacing(b"hello", 0.1)),
    )

    atomic_reader.start()
    await asyncio.sleep(0)
    await atomic_reader.stop(2 * 0.1)

    assert atomic_reader.buffer == b"he"


async def test_reader_exception():
    """Make sure a reader exception is handled correctly."""
    # TODO check that done callback logs the error
    with pytest.raises(RuntimeError):
        async with AtomicLineReader(ExceptionalReadable()):
            await asyncio.sleep(0)  # allow read to happen -> exception in task
            await asyncio.sleep(0.1)  # allow task.done_callback to execute


async def test_kill_reader_while_awaiting_line():
    async with AtomicLineReader(
        MockReadable(bytestream_equal_spacing(b"hello", 0.1)),
    ) as reader:
        read_task = asyncio.create_task(reader.readline())
        await reader.stop()

        async with asyncio.timeout(1):
            with pytest.raises(LinesProcessError):
                await read_task
