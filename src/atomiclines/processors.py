import re
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, TypeAlias

from atomiclines.lineprocessor import LineHolder, LineProcessor

async_predicate_type: TypeAlias = Callable[
    [LineHolder],
    Awaitable[bool],
]


def regex_predicate(regex: re.Pattern[bytes]) -> async_predicate_type:
    """Predicate to check if line matches regex.

    Args:
        regex: regex to match against

    Returns:
        An async_predicate_type predicate, which returns true if the line matches the regex.
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


class LineProcessingFuncBase(ABC):
    """Base Class for Callable object to be used as processor functions for LineProcessor.

    Provides a back reference to the LineProcessor in the `lineprocessor` property.
    DO not add the same instance to different LineProcessors.
    """

    def __init__(self, processor: LineProcessor.processor_type) -> None:
        """Initialization.

        Args:
            processor: Processor function to apply when this object is __call__()ed.
        """
        # TODO: should we call an abstractmethod __call__()?
        self._lineprocessor: LineProcessor | None = (
            None  # TODO: should we call this parent or something else?
        )
        self._processor: LineProcessor.processor_type = processor

    @property
    def lineprocessor(self) -> LineProcessor:
        """_summary_

        Raises:
            RuntimeError: When the property is accessed before the LineProcessor initialized it
                (during the addProcessor call)

        Returns:
            the parent LineProcessor object the processor is assigned to.
        """
        if self._lineprocessor is None:
            raise RuntimeError(  # TODO: custom exception
                "Backreference self._lineprocessor was never initialized.",
            )

        return self._lineprocessor

    @abstractmethod
    async def __call__(self, line_holder: LineHolder) -> bool | None:
        raise NotImplementedError


class ProcessUntil(LineProcessingFuncBase):
    """Apply processor until predicate returns true.

    Automagically removes processor function from Lineporcessor once predicate matches
    """

    def __init__(
        self,
        processor: LineProcessor.processor_type,
        predicate: async_predicate_type,
        inclusive: bool = True,
    ) -> None:
        """Init.

        Args:
            processor: processor to apply
            predicate: predicate function to decide if processing is stopped.
            inclusive: If true the line matching the predicate is also fed to the processor. Defaults to True.
        """
        super().__init__(processor)
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
        """Actual processor implementation

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
