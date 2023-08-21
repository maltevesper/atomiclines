from unittest.mock import patch

import pytest

from atomiclines.log import try_load_config_from_environment


def test_log_env_config_nonexistent_variable():
    # this should not throw
    with patch("os.environ.get", return_value=None):
        try_load_config_from_environment("somevar")


def test_log_env_config_nonexistent_file():
    with patch("pathlib.Path.read_text", side_effect=FileNotFoundError()), patch(
        "os.environ.get", return_value="virtualfile.txt"
    ):
        with pytest.raises(FileNotFoundError):
            try_load_config_from_environment("somevar")