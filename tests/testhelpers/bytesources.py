"""Byte generators to be used as datasources."""
import asyncio
import re
from collections.abc import AsyncIterator

from more_itertools import chunked


class RefillableBytestream:
    """Bytestream, which can be extended during use."""

    def __init__(self, bytesequence: bytes | bytearray) -> None:
        """Initialize RefillableBytestream.

        Args:
            bytesequence: initial bytes to steam.
        """
        self._bytesequence: bytearray = bytearray(bytesequence)
        self._running = True
        self._data_ready_event = asyncio.Event()
        self._data_ready_event.set()

    async def stream(self) -> AsyncIterator[bytes]:
        """Stream bytes out.

        Yields:
            _Bytes (one by one) from the bytesequence provided in init/append.
        """
        while self._running:
            await self._data_ready_event.wait()
            self._data_ready_event.clear()
            for byte in self._bytesequence:
                yield bytes([byte])

            self._bytesequence = bytearray()

    def append(self, bytesequence: bytes) -> None:
        """Add additional bytes to be streamed.

        Args:
            bytesequence: bytes to append.
        """
        self._bytesequence.extend(bytesequence)
        self._data_ready_event.set()


async def bytestream_zero_delay(bytesequence: bytes) -> AsyncIterator[bytes]:
    """Return single bytes from a bytes object.

    Args:
        bytesequence: bytesequence to iterate over

    Yields:
        single bytes from bytesequence
    """
    for byte in bytesequence:
        yield bytes([byte])


async def bytestream_equal_spacing(
    bytesequence: bytes,
    interval_s: float = 0,
) -> AsyncIterator[bytes]:
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


async def bytestream_line_chunked(
    bytesequence: bytes,
    interval_s: float = 0,
) -> AsyncIterator[bytes]:
    r"""Return lines from bytesequence and add delay between.

    Args:
        bytesequence: byte sequence to yeild from
        interval_s: delay between bytes. Defaults to 0.

    Yields:
        bytechunks with trailing \n from bytesequence.
    """
    for chunk in re.split(rb"(?<=\n)", bytesequence):
        yield chunk
        await asyncio.sleep(interval_s)


async def multibytestream_equal_spacing(
    bytesequence: bytes,
    interval_s: float = 0,
) -> AsyncIterator[bytes]:
    """Return bytes from bytesequence and add delay between.

    Args:
        bytesequence: byte sequence to yeild from
        interval_s: delay between bytes. Defaults to 0.

    Yields:
        two bytes from bytesequence.
    """
    for byte_chunk in chunked(bytesequence, 2):
        yield bytes(byte_chunk)
        await asyncio.sleep(interval_s)


async def bytestream_zero_reads(bytesequence: bytes) -> AsyncIterator[bytes]:
    """Return single bytes from a bytes object and empty reads inbetween.

    Args:
        bytesequence: bytesequence to iterate over

    Yields:
        single bytes from bytesequence or empty bytes object
    """
    for byte in bytesequence:
        yield bytes([byte])
        yield b""
