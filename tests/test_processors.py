import asyncio
import re
from unittest.mock import AsyncMock, call

import pytest

from atomiclines.lineprocessor import LineHolder, LineProcessor
from atomiclines.processors import LineProcessingFuncBase, ProcessUntil, regex_predicate
from tests.testhelpers.bytesources import bytestream_zero_delay
from tests.testhelpers.readable import MockReadable


async def drop_all(line_holder: LineHolder):
    return True


async def test_processor_process_until():
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    processor_capture = AsyncMock(return_value=None)
    line_processor.add_processor(ProcessUntil(drop_all, regex_predicate(b"ok")))
    line_processor.add_processor(processor_capture)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert processor_capture.call_args_list == [
        call(LineHolder(line[0].rstrip(b"\n")))
        for line in re.finditer(
            b"(.*?)\n",
            re.split(b"(^|\n)ok\n", bytestream, maxsplit=1)[-1],
        )
    ]


async def test_processor_process_until_exclusive():
    bytestream = (
        b"hello\nworld\nok\nmany\nlines\nso\nmany\nmore\nlines\ncoke\nis\nsomething\na"
    )
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay(bytestream)))
    processor_capture = AsyncMock(return_value=None)
    line_processor.add_processor(ProcessUntil(drop_all, regex_predicate(b"ok"), False))
    line_processor.add_processor(processor_capture)

    async with line_processor:
        await asyncio.sleep(0.1)

    assert processor_capture.call_args_list == [
        call(LineHolder(line[0].rstrip(b"\n")))
        for line in re.finditer(
            b"(.*?)\n",
            re.split(b"(^|\n)(?=ok\n)", bytestream, maxsplit=1)[-1],
        )
    ]


async def test_LineProcessingFuncBase_uninitalized_parent():
    line_processor = LineProcessor(MockReadable(bytestream_zero_delay("")))
    unbound_base = ProcessUntil(line_processor, regex_predicate(""))

    with pytest.raises(
        RuntimeError,
        match=re.escape("Backreference self._lineprocessor was never initialized."),
    ):
        unbound_base.lineprocessor
