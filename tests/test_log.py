"""Test log config loading."""
from unittest.mock import patch

import pytest
from atomiclines.log import try_load_config_from_environment


def test_log_env_config_nonexistent_variable() -> None:
    """Test that unset environment variable does not cause an error."""
    # this should not throw
    with patch(
        "os.environ.get",
        return_value=None,
    ):  # TODO: use a pytest fixture instead
        try_load_config_from_environment("somevar")


def test_log_env_config_nonexistent_file() -> None:
    """Test error generation if logfile can not be found."""
    with (  # separating pytest.raises from the rest for clarity
        patch("pathlib.Path.read_text", side_effect=FileNotFoundError()),
        patch("os.environ.get", return_value="virtualfile.txt"),
    ):
        with pytest.raises(FileNotFoundError):
            try_load_config_from_environment("somevar")
