"""Test the LineProcessor module."""
import asyncio
import re
import time
from typing import Literal, TypeVar
from unittest.mock import DEFAULT, AsyncMock, Mock, call

from atomiclines.lineprocessor import (
    LineHolder,
    LineProcessingFuncBase,
    LineProcessor,
    wrap_as_async,
)
from testhelpers.bytesources import (
    RefillableBytestream,
    bytestream_equal_spacing,
    bytestream_line_chunked,
    bytestream_zero_delay,
)
from testhelpers.readable import MockReadable


async def processor_True(_line: LineHolder) -> Literal[True]:
    """Lineprocessor which always returns True.

    Args:
        _line: _line(holder) to process

    Returns:
        True
    """
    return True


async def processor_False(_line: LineHolder) -> Literal[False]:
    """Lineprocessor which always returns False.

    Args:
        _line: _line(holder) to process

    Returns:
        False
    """
    return False


async def test_lineholder_str() -> None:
    """Test str representation of LineHolder."""
    line = "atomic"
    assert str(LineHolder(line.encode())) == line


async def test_lineholder_repr() -> None:
    """Test repr of LineHolder."""
    line = "lines"
    assert repr(LineHolder(line.encode())) == f"<LineHolder({line})>"


async def test_lineholder_eq() -> None:
    """Test eq comparison of LineHolder."""
    line_a = LineHolder(b"a")
    line_b = LineHolder(b"b")

    assert line_a != line_b
    assert line_a == line_a  # noqa: PLR0124 test that identity equal holds
    assert line_a == LineHolder(b"a")

    assert line_a != b"a"


async def test_lineprocessor() -> None:
    """Test baseline functionality of LineProcessor."""
    bytestream = b"hello\nworld\nok"
    processor = AsyncMock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    line_processor.add_processor(processor)

    async with line_processor:
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    assert processor.call_args_list == [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(b"(.*?)\n", bytestream)
    ]


async def test_lineprocessor_remove() -> None:
    """Test removal of a lineprocessor."""
    bytestream_start = b"hello\nworld\nok"
    bytestream_extension = b"\ngoodbye\ncruel\nworld\nnot ok"
    bytestream = RefillableBytestream(bytestream_start)
    processor_a = AsyncMock(return_value=None)
    processor_b = AsyncMock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream.stream()))
    line_processor.add_processor(processor_a)
    processor_b_handle = line_processor.add_processor(processor_b)[0]

    async with line_processor:
        await asyncio.sleep(0.1)
        line_processor.remove_processor(processor_b_handle)
        bytestream.append(bytestream_extension)
        await asyncio.sleep(0.1)

    assert processor_a.call_args_list == [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(
            b"(.*?)\n",
            bytestream_start + bytestream_extension,
        )
    ]
    assert processor_b.call_args_list == [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(b"(.*?)\n", bytestream_start)
    ]


async def test_lineprocessor_no_bubble() -> None:
    """Test bubbling surpression of lineprocessor."""
    bytestream_start = b"hello\nworld\nok"
    bytestream = RefillableBytestream(bytestream_start)

    def filtering_processor(line: LineHolder) -> bool:
        return line.line == b"world"

    processor_a = AsyncMock(side_effect=filtering_processor, return_value=DEFAULT)
    processor_b = AsyncMock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream.stream()))
    line_processor.add_processor(processor_a)
    line_processor.add_processor(processor_b)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert processor_a.call_args_list == [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(
            b"(.*?)\n",
            bytestream_start,
        )
    ]
    assert processor_b.call_args_list == [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(b"(.*?)\n", bytestream_start)
        if line_match[1] != b"world"
    ]


def slow_processor(_line: LineHolder) -> None:
    """A processor which blocks for a while.

    Args:
        _line: line to process.
    """
    time.sleep(0.1)  # currently we do not process the lines asynchronously...


async def test_lineprocessor_softstop() -> None:
    """Test gentle shutdown with timeout."""
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(
        MockReadable(bytestream_equal_spacing(bytestream, 0.01)),
    )
    processor = AsyncMock(side_effect=slow_processor, return_value=DEFAULT)
    line_processor.add_processor(processor)

    async with asyncio.timeout(0.2):
        async with line_processor:
            await asyncio.sleep(0.07)  # allow data for one element to be buffered
            await line_processor.stop(1)

    assert processor.call_count == 1


async def test_lineprocessor_hardstop() -> None:
    """Test forced stop."""
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    processor = AsyncMock(side_effect=slow_processor, return_value=DEFAULT)
    line_processor.add_processor(processor)

    async with asyncio.timeout(0.2):
        async with line_processor:
            await line_processor.stop(0)

    assert (
        processor.call_count == 1
    )  # await stop, allows a switch and allows one item to process.


async def test_lineprocessor_stopsignal() -> None:
    """Test stop signal without timeout."""
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(
        MockReadable(bytestream_equal_spacing(bytestream, 0.01)),
    )

    async def processor(_line: LineHolder) -> None:
        line_processor.signal_stop()

    line_processor.add_processor(processor)

    async with asyncio.timeout(0.2):
        async with line_processor:
            await asyncio.sleep(0.1)
            assert line_processor.background_task_active is False


async def test_lineprocessor_modification() -> None:
    """Test modifying line from LineProcessor."""
    bytestream_start = b"hello\nworld\nok"
    bytestream = RefillableBytestream(bytestream_start)

    async def uppercase_processor(line: LineHolder) -> None:
        line.line = line.line.upper()

    mock_postprocessor = AsyncMock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream.stream()))
    line_processor.add_processor(uppercase_processor)
    line_processor.add_processor(mock_postprocessor)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert mock_postprocessor.call_args_list == [
        call(LineHolder(line_match[1].upper()))
        for line_match in re.finditer(
            b"(.*?)\n",
            bytestream_start,
        )
    ]


async def test_lineprocessor_temporary() -> None:
    """Read a line, temporarily throw away everything, read some more."""
    bytestream = b"hello\nworld\nok\nmore\nd"
    processor = AsyncMock(return_value=None)
    line_processor = LineProcessor(
        MockReadable(bytestream_line_chunked(bytestream, 0.1)),
        # alternative? EOFReadable(bytestream_line_chunked(bytestream, 0.1)),
    )
    line_processor.add_processor(processor)

    async with line_processor:
        await asyncio.sleep(0.05)

        with line_processor.temporary_processor(processor_True):
            await asyncio.sleep(0.2)

        await asyncio.sleep(1)

    assert processor.call_args_list == [
        call(LineHolder(chunk))
        for index, chunk in enumerate(
            re.split(
                rb"\n",
                bytestream,
            )[:-1],  # Throw away trailing bytes which are not yielded by linereader
        )
        if index not in {1, 2}
    ]


async def test_lineporcessor_add_remove() -> None:
    """Test addition and removal of processors."""
    line_processor = LineProcessor(
        MockReadable(bytestream_line_chunked(b"", 0.1)),
    )

    processor_a = line_processor.add_processor(processor_True)[0]

    assert [processor_a] == line_processor.processors

    processor_b = line_processor.add_processor(processor_True)[0]
    processor_c = line_processor.add_processor(processor_True)[0]

    assert [processor_a, processor_b, processor_c] == line_processor.processors

    line_processor.remove_processor(processor_b)

    assert [processor_a, processor_c] == line_processor.processors


async def test_lineprocessor_temporary_index() -> None:
    """Test the index argument of temporary_processor()."""
    line_processor = LineProcessor(
        MockReadable(bytestream_line_chunked(b"", 0.1)),
    )

    processor_a = line_processor.add_processor(processor_True)[0]

    assert [processor_a] == line_processor.processors

    with line_processor.temporary_processor([processor_True, processor_False]):
        assert [
            processor_True,
            processor_False,
            processor_a,
        ] == line_processor.processors

    assert [processor_a] == line_processor.processors

    with line_processor.temporary_processor([processor_True, processor_False], 1):
        assert [
            processor_a,
            processor_True,
            processor_False,
        ] == line_processor.processors

    assert [processor_a] == line_processor.processors


async def test_lineporcessor_temporary_reentrancy() -> None:
    """Make sure that temporary_processor works reentrantly."""
    line_processor = LineProcessor(
        MockReadable(bytestream_line_chunked(b"", 0.1)),
    )

    processor_a = line_processor.add_processor(processor_True)[0]

    assert [processor_a] == line_processor.processors

    with line_processor.temporary_processor(processor_True):
        assert [processor_True, processor_a] == line_processor.processors

        with line_processor.temporary_processor([processor_False], 1):
            assert [
                processor_True,
                processor_False,
                processor_a,
            ] == line_processor.processors

    assert [processor_a] == line_processor.processors


async def test_lineprocessor_processorlist_modification() -> None:
    """Test live modifcation of active processors.

    Processing the list of processors could from a process could cause issues,
    if we modify the same list as the one used for looping.

    This test is supposed to check that the process immediatly after the self
    removing process is not skipped when the process removes it self.

    >>> l=[1,2,3]
    >>> for i in l:
    ...     if i == 1:
    ...         l.remove(i)
    ...     print(i)
    1
    3
    """
    bytestream = b"a\nb\n"
    line_processor = LineProcessor(
        MockReadable(bytestream_zero_delay(bytestream)),
    )

    async def processor_self_removing(_line: LineHolder) -> None:
        line_processor.remove_processor(processor_self_removing)

    processor_a = AsyncMock(return_value=None)
    processor_b = AsyncMock(return_value=None)

    line_processor.add_processor(processor_self_removing)
    line_processor.add_processor(processor_a)
    line_processor.add_processor(processor_b)

    async with line_processor:
        await asyncio.sleep(0.1)

    expected_calls = [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(
            b"(.*?)\n",
            bytestream,
        )
    ]

    assert expected_calls == processor_a.call_args_list
    assert expected_calls == processor_b.call_args_list


T = TypeVar("T")


async def test_wrap_as_async() -> None:
    """Cruedly test that wrap as async calls wrapped function."""

    # TODO: use unittest mock and call history to test
    def identity(x: T) -> T:
        return x

    for x in (1, None, "42"):
        assert identity(x) == await wrap_as_async(identity)(x)


async def test_apply_wrap_as_async() -> None:
    """Test wrap_as_async helper."""
    bytestream = b"hello\nworld\nok"
    processor = Mock(return_value=None)
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    line_processor.add_processor(wrap_as_async(processor))

    async with line_processor:
        await asyncio.sleep(0)

    assert processor.call_args_list == [
        call(LineHolder(line_match[1]))
        for line_match in re.finditer(b"(.*?)\n", bytestream)
    ]


class ProcessingObject(LineProcessingFuncBase):
    """Simple processing object test."""

    async def __call__(self, _line_holder: LineHolder) -> bool | None:
        """Processing function implementation."""
        return True


async def test_LineProcessingFuncBase_temporary() -> None:
    """Test LineProcessorFuncBase with temporary()."""
    line_processor = LineProcessor(
        MockReadable(bytestream_zero_delay(b"")),
    )

    processor = ProcessingObject()

    async with line_processor:
        with line_processor.temporary_processor(processor):
            processor.lineprocessor.remove_processor(processor)
