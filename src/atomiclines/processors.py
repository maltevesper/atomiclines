"""Prebuild processors for use with LineProcessor."""

import re
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from atomiclines.lineprocessor import LineHolder, LineProcessingFuncBase, LineProcessor

AsyncPredicate: TypeAlias = Callable[
    [LineHolder],
    Awaitable[bool],
]


def regex_predicate(regex: re.Pattern[bytes]) -> AsyncPredicate:
    """Predicate to check if line matches regex.

    Args:
        regex: regex to match against

    Returns:
        An AsyncPredicate which returns true if the line matches the regex.
    """
    compiled_regex = re.compile(regex)

    async def predicate(line_holder: LineHolder) -> bool:
        """Return true if the line matches the regex of the closure.

        Args:
            line_holder: LineHolder object for which to evaluate the predicate

        Returns:
            True if LineHolder.line matches the regex
        """
        return bool(compiled_regex.match(line_holder.line))

    return predicate


class ProcessUntil(LineProcessingFuncBase):
    """Apply processor until predicate returns true.

    Automagically removes processor function from Lineporcessor once predicate matches
    """

    def __init__(
        self,
        processor: LineProcessor.ProcessorType,
        predicate: AsyncPredicate,
        *,
        inclusive: bool = True,
    ) -> None:
        """Init.

        Args:
            processor: processor to apply
            predicate: predicate function to decide if processing is stopped.
            inclusive: If true the line matching the predicate is also fed to the
                processor. Defaults to True.
        """
        super().__init__()
        self._processor = processor
        self._predicate = predicate
        self._inclusive = inclusive

    @property
    def inclusive(self) -> bool:
        """`inclusive` property.

        Returns:
            value of inclusive property
        """
        return self._inclusive

    # @override
    async def __call__(self, line_holder: LineHolder) -> bool | None:
        """Actual processor implementation.

        Args:
            line_holder: current lineholder for line being processed

        Returns:
            True if line should not be processed by further processors.
        """
        if await self._predicate(line_holder):
            self.lineprocessor.remove_processor(self)

            if not self.inclusive:
                return False

        return await self._processor(line_holder)
