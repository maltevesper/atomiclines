"""The atomic-lines package."""

from atomiclines.atomiclinereader import AtomicLineReader
from atomiclines.backgroundtask import BackgroundTask
from atomiclines.lineprocessor import LineHolder, LineProcessor
from atomiclines.log import logger, try_load_config_from_environment

__all__ = [
    "AtomicLineReader",
    "BackgroundTask",
    "LineHolder",
    "LineProcessor",
    "logger",
]

try_load_config_from_environment("ATOMICLINES_LOG_CONFIG")
