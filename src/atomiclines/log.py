import logging
import os
from logging.config import DictConfigurator
from pathlib import Path

import yaml

logger = logging.getLogger("atomiclines")


def load_config_from_yaml(config_file_path: str | os.PathLike) -> None:
    """Load configuration from file.

    Args:
        config_file_path: _description_
    """
    config_file = Path(config_file_path)

    # Let this throw, if the config file does not exist, you want to know.
    # ... and logging is not configured as you expect yet, so logging is not
    # an option
    configuration = yaml.safe_load(config_file.read_text(encoding="utf-8"))

    DictConfigurator(configuration).configure()


def try_load_config_from_environment(environment_variable: str) -> None:
    """Load configuration from file specified in environment variable.

    Args:
        environment_variable: name of environment variable holding path to config file.
    """
    config_file_path = os.environ.get(environment_variable, None)

    if config_file_path:
        load_config_from_yaml(config_file_path)
