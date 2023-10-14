import asyncio
import io
import logging

import pytest
from testhelpers.bytesources import (
    bytestream_equal_spacing,
    bytestream_zero_delay,
    bytestream_zero_reads,
    multibytestream_equal_spacing,
)
from testhelpers.readable import EOFReadable, ExceptionalReadable, MockReadable

from atomiclines.atomiclinereader import AtomicLineReader
from atomiclines.exception import LinesEOFError, LinesTimeoutError
from atomiclines.log import logger


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

    with caplog.at_level(logging.INFO, logger.name):
        async with AtomicLineReader(
            MockReadable(multibytestream_equal_spacing(bytestream, 0.01)),
        ) as atomic_reader:
            assert bytesreader.readline().strip() == await atomic_reader.readline(0.1)
            assert bytesreader.readline().strip() == await atomic_reader.readline(0.1)
            await asyncio.sleep(0.1)

    assert caplog.messages == list(map(str, bytestream.split(b"\n")[:-1]))


async def test_readline_0bytes():
    pass


async def test_readline_eof():
    bytestream = b"hello\nworld"
    bytesreader = io.BytesIO(bytestream)
    reached_end = False

    with pytest.raises(LinesEOFError):
        async with AtomicLineReader(
            EOFReadable(bytestream_zero_delay(bytestream)),
        ) as atomic_reader:
            assert bytesreader.readline().strip() == await atomic_reader.readline(
                timeout=0.1,
            )
            # await asyncio.sleep(0.1)
            assert bytesreader.readline().strip() == await atomic_reader.readline(
                timeout=0.1,
            )

            with pytest.raises(LinesEOFError):
                await atomic_reader.readline(timeout=5)

            reached_end = True

    assert reached_end  # make sure enough of the test code inside the pytest.raises is executed


async def test_readline_eof_eol():
    bytestream = b"hello\nworld\n"
    bytesreader = io.BytesIO(bytestream)
    reached_end = False

    with pytest.raises(LinesEOFError):
        async with AtomicLineReader(
            EOFReadable(bytestream_zero_reads(bytestream)),
        ) as atomic_reader:
            assert bytesreader.readline().strip() == await atomic_reader.readline(
                timeout=0.1,
            )
            assert bytesreader.readline().strip() == await atomic_reader.readline(
                timeout=0.1,
            )

            with pytest.raises(LinesEOFError):
                await atomic_reader.readline(timeout=5)

            reached_end = True

    assert reached_end


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


async def test_reader_exception(caplog: pytest.LogCaptureFixture):
    """Make sure a reader exception is handled correctly."""
    with caplog.at_level(logging.INFO):
        with pytest.raises(RuntimeError):
            async with AtomicLineReader(ExceptionalReadable()):
                await asyncio.sleep(0)  # allow read to happen -> exception in task
                await asyncio.sleep(0.1)  # allow task.done_callback to execute

    assert caplog.messages[0].startswith("An error occured in the background process.")


async def test_kill_reader_while_awaiting_line():
    async with AtomicLineReader(
        MockReadable(bytestream_equal_spacing(b"hello", 0.1)),
    ) as reader:
        read_task = asyncio.create_task(reader.readline())
        await reader.stop()

        async with asyncio.timeout(1):
            with pytest.raises(asyncio.exceptions.CancelledError):
                await reader.readline(0)

            with pytest.raises(asyncio.exceptions.CancelledError):
                await read_task
