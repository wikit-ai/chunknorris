import logging
from typing import Literal

LOGGER = logging.getLogger("ChunkNorris")
LOGGER.addHandler(logging.NullHandler())

_LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def set_log_level(
    level: Literal["debug", "info", "warning", "error", "critical"],
) -> None:
    """Set ChunkNorris log level.

    Args:
        level: one of "debug", "info", "warning", "error", "critical"
    """
    LOGGER.setLevel(_LEVELS[level])
