# Introduction

A library to help with atomic processing of lines. Some libraries are a bit fuzzy on what happens if a call
to `readline` times out (is the partial read data consumed? Is a partial read returned?). This can be used 
as an adapter for such libraries as long as they have an ordinary `read` call.

## Overview

The [AtomicLineReader][atomiclines.atomiclinereader.AtomicLineReader] provides a sane `readline` function internally. [LineProcessor][atomiclines.lineprocessor.LineProcessor] extends this by running an AtomicLineReader][atomiclines.atomiclinereader.AtomicLineReader] and then running any user provided processing function on each line.

The library is implemented as async.

## Example

Assume you would like to do read lines from the serial port asynchronously.

???+ note

    Accoridng to my best knowledge cross platform async access to the serial port is hard, and is the reason why this was created (and for me to have a proper play with async ;) )

``` python
import asyncio

import aioserial
from atomiclines.lineprocessor import LineProcessor


class SerialReadable:
    """A wrapper to back up AioSerial so that the interface matches
    LineProcessor/AtomicLineReader's expectations."""
    def __init__(self, port):
        self._serial = aioserial.AioSerial(port=port, baudrate=115200)

    async def read(self):
        return await self._serial.read_async()


async def main():
    readable = SerialReadable("/dev/ttyUSB0")

    processor = LineProcessor(readable)
    processor.add_processor(lambda x: print(x.line))  # (1)!

    async with processor:  # (2)!
        readable._serial.write(b"help\r\n")  # (3)!
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
```

1.  We just print every line, like a terminal
2.  I am a strong believer in preventing users from forgetting to do cleanup through the use of contextmanagers.
    Otherwise cleanup might be ommitted, like the closing of the AioSerial port in this example.
3.  A command which the serial counterpart hopefully understands