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
    # Ensure at least one real handler is present so logs are actually emitted.
    # The NullHandler added at module level is only a silent placeholder for
    # applications that configure no logging at all.
    if not any(not isinstance(h, logging.NullHandler) for h in LOGGER.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s - %(name)s - %(message)s")
        )
        LOGGER.addHandler(handler)
