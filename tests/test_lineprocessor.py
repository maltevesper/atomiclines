import asyncio
import contextlib
import re
import time
import typing
from unittest.mock import DEFAULT, Mock, call

from atomiclines.lineprocessor import LineProcessor


# TODO: factor testhelper methods out in submodules
class RefillableBytestream:
    def __init__(self, bytesequence: bytes | bytearray) -> None:
        self._bytesequence: bytearray = bytearray(bytesequence)
        self._running = True
        self._data_ready_event = asyncio.Event()
        self._data_ready_event.set()

    async def stream(self) -> typing.AsyncGenerator[bytes, None]:
        while self._running:
            await self._data_ready_event.wait()
            self._data_ready_event.clear()
            for byte in self._bytesequence:
                yield bytes([byte])

            self._bytesequence = bytearray()

    def append(self, bytesequence: bytes) -> None:
        self._bytesequence.extend(bytesequence)
        self._data_ready_event.set()


async def bytestream_zero_delay(bytesequence: bytes):
    """Return single bytes from a bytes object.

    Args:
        bytesequence: bytesequence to iterate over

    Yields:
        single bytes from bytesequence
    """
    for byte in bytesequence:
        yield bytes([byte])


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


async def test_lineprocessor():
    bytestream = b"hello\nworld\nok"
    processor = Mock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    line_processor.add_processor(processor)

    async with line_processor:
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    assert processor.call_args_list == [
        call(line_match[1]) for line_match in re.finditer(b"(.*?)\n", bytestream)
    ]

    # await line_processor.stop()


async def test_lineprocessor_remove():
    bytestream_start = b"hello\nworld\nok"
    bytestream_extension = b"\ngoodbye\ncruel\nworld\nnot ok"
    bytestream = RefillableBytestream(bytestream_start)
    processor_a = Mock(return_value=None)
    processor_b = Mock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream.stream()))
    line_processor.add_processor(processor_a)
    line_processor.add_processor(processor_b)

    async with line_processor:
        await asyncio.sleep(0.1)
        line_processor.remove_processor(processor_b)
        bytestream.append(bytestream_extension)
        await asyncio.sleep(0.1)

    assert processor_a.call_args_list == [
        call(line_match[1])
        for line_match in re.finditer(
            b"(.*?)\n",
            bytestream_start + bytestream_extension,
        )
    ]
    assert processor_b.call_args_list == [
        call(line_match[1]) for line_match in re.finditer(b"(.*?)\n", bytestream_start)
    ]


async def test_lineprocessor_no_bubble():
    bytestream_start = b"hello\nworld\nok"
    bytestream = RefillableBytestream(bytestream_start)

    def filtering_processor(line):
        return line == b"world"

    processor_a = Mock(side_effect=filtering_processor, return_value=DEFAULT)
    processor_b = Mock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream.stream()))
    line_processor.add_processor(processor_a)
    line_processor.add_processor(processor_b)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert processor_a.call_args_list == [
        call(line_match[1])
        for line_match in re.finditer(
            b"(.*?)\n",
            bytestream_start,
        )
    ]
    assert processor_b.call_args_list == [
        call(line_match[1])
        for line_match in re.finditer(b"(.*?)\n", bytestream_start)
        if line_match[1] != b"world"
    ]


def slow_processor(line):
    time.sleep(0.1)  # currently we do not process the lines asynchronously...


async def test_lineprocessor_softstop():
    # TODO: this test does not really test a lot...
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(
        MockReadable(bytestream_equal_spacing(bytestream, 0.01)),
    )
    processor = Mock(side_effect=slow_processor, return_value=DEFAULT)
    line_processor.add_processor(processor)

    async with asyncio.timeout(0.2):
        async with line_processor:
            await asyncio.sleep(0.07)  # allow data for one element to be buffered
            await line_processor.stop(1)

    assert processor.call_count == 1


async def test_lineprocessor_hardstop():
    # TODO: this test does not really test a lot...
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    processor = Mock(side_effect=slow_processor, return_value=DEFAULT)
    line_processor.add_processor(processor)

    async with asyncio.timeout(0.2):
        async with line_processor:
            await line_processor.stop(0)

    assert (
        processor.call_count == 1
    )  # await stop, allows a switch and allows one item to process.


async def test_lineprocessor_stopsignal():
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(
        MockReadable(bytestream_equal_spacing(bytestream, 0.01)),
    )

    def processor(line):
        line_processor.signal_stop()

    line_processor.add_processor(processor)

    async with asyncio.timeout(0.2):
        async with line_processor:
            await asyncio.sleep(0.1)
            assert line_processor.background_task_active is False
