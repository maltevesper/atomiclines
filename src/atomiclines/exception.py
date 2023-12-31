"""Exceptions for atomiclines."""


class LinesException(  # noqa: N818 omitt error suffix like the std library base
    # Exception
    Exception,
):
    """Base exception class for atomiclines library.

    All exceptions we expect should be based on this,
    so a library user can `except LinesException`.
    """


class LinesEOFError(LinesException):
    """Exception to report EOF from reader."""


class LinesTimeoutError(LinesException):
    """Timeout exception.

    Stores the timeout in seconds which elapsed.
    """

    def __init__(self, timeout: float) -> None:
        """Initialize new timeout exception.

        Args:
            timeout: timeout in seconds.
        """
        self._timeout = timeout
        super().__init__(timeout)

    @property
    def timeout(self) -> float:
        """Timeout as a read only property.

        Returns:
            timeout in seconds.
        """
        return self._timeout

    def __str__(self) -> str:
        """Generate String representation.

        Returns:
            string representation.
        """
        return f"Timeout of {self.timeout} seconds expired."


class LinesProcessError(LinesException):
    """Errors generated by a lines process."""
