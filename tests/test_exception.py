from atomiclines.exception import LinesTimeoutError


def test_timeout():
    timeout = 1.5
    lines_timeout = LinesTimeoutError(timeout)

    assert timeout == lines_timeout.timeout
    assert str(lines_timeout) == f"Timeout of {timeout} seconds expired."
