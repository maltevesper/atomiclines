"""The atomic-lines package."""

from atomiclines import log

log.try_load_config_from_environment("LINE_LOG_CONFIG")
