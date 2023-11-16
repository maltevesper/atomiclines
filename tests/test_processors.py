"""Test processing functions."""
import asyncio
import re
from typing import Literal
from unittest.mock import AsyncMock, call

import pytest
from atomiclines.lineprocessor import LineHolder, LineProcessor
from atomiclines.processors import ProcessUntil, regex_predicate

from tests.testhelpers.bytesources import bytestream_zero_delay
from tests.testhelpers.readable import MockReadable


async def drop_all(_line_holder: LineHolder) -> Literal[True]:
    """Processor function which stops any further processing of the line.

    Args:
        line_holder: LineHolder

    Returns:
        Literal[True]
    """
    return True


async def test_processor_process_until() -> None:
    """Test ProcessUntil by consuming everythin up to a sentinel (include sentinel)."""
    sentinel = b"ok"
    pre_sentinel = b"hello\nworld\n"
    post_sentinel = b"many\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"

    bytestream = pre_sentinel + sentinel + b"\n" + post_sentinel

    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    processor_capture = AsyncMock(return_value=None)

    line_processor.add_processor(
        ProcessUntil(drop_all, regex_predicate(re.escape(sentinel))),
    )
    line_processor.add_processor(processor_capture)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert processor_capture.call_args_list == [
        call(LineHolder(line[0].rstrip(b"\n")))
        for line in re.finditer(
            b"(.*?)\n",
            post_sentinel,
        )
    ]


async def test_processor_process_until_exclusive() -> None:
    """Test ProcessUntil by consuming everythin up to a sentinel (exclude sentinel)."""
    sentinel = b"ok"
    pre_sentinel = b"hello\nworld\n"
    post_sentinel = b"many\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"

    bytestream = pre_sentinel + sentinel + b"\n" + post_sentinel

    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    processor_capture = AsyncMock(return_value=None)
    line_processor.add_processor(
        ProcessUntil(drop_all, regex_predicate(re.escape(sentinel)), inclusive=False),
    )
    line_processor.add_processor(processor_capture)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert processor_capture.call_args_list == [
        call(LineHolder(line[0].rstrip(b"\n")))
        for line in re.finditer(
            b"(.*?)\n",
            sentinel + b"\n" + post_sentinel,
        )
    ]


async def test_LineProcessingFuncBase_uninitalized_parent() -> None:
    """Test exception when attemtping to use `uninitialized` processor."""
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay("")))
    unbound_base = ProcessUntil(line_processor, regex_predicate(""))

    with pytest.raises(
        RuntimeError,
        match=re.escape("Backreference self._lineprocessor was never initialized."),
    ):
        unbound_base.lineprocessor  # noqa: B018  this will raise our exception


async def test_LineProcessingFuncBase_rebind() -> None:
    """Test that rebinding a processor throws an exception."""
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay("")))
    processor_function = ProcessUntil(line_processor, regex_predicate(""))
    line_processor.add_processor(processor_function)

    with pytest.raises(RuntimeError, match="already bound"):
        line_processor.add_processor(processor_function)
