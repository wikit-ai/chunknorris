import logging
import os
import threading
import time
from contextlib import contextmanager
from functools import wraps
from inspect import signature
from typing import Any, Callable, Generator

import psutil

from ..core.logger import LOGGER  # pylint: disable=E0402

MEMORY_WARNING_LIMIT = 800


def validate_args(function: Callable[..., Any]) -> Any:
    """Meant to be used as a decorator : @validate_args.
    Checks that the types of arguments passed to a function
    matches the typing provided.

    Note : pydantic proposes a similar decorator : @validate_call.
    HOWEVER, this causes an error when applied to __ini__() functions.

    Args:
        function (Callable[..., Any]): any typed function.

    Returns:
        Any: the return of the function.
    """

    @wraps(function)
    def wrapper(*args: tuple[Any], **kwargs: dict[Any, Any]) -> Any:
        sig = signature(function)
        for arg_name, arg_value in zip(sig.parameters, args):
            if (
                sig.parameters[arg_name].annotation
                is not sig.parameters[arg_name].empty
            ):
                if not isinstance(arg_value, sig.parameters[arg_name].annotation):
                    raise ValueError(
                        f"Argument '{arg_name}' must be of type {sig.parameters[arg_name].annotation.__name__}."
                    )
        result = function(*args, **kwargs)

        return result

    return wrapper


@contextmanager
def mem_debug(label: str, sample_interval: float = 0.05) -> Generator[None, None, None]:
    """Context manager that logs memory usage and duration at DEBUG level.
    Completely skipped (no psutil call, no thread) when log level is above DEBUG.

    Tracks both peak RSS (via a background sampler) and net RSS change, since
    memory freed inside the block would otherwise make the peak invisible.

    Usage:
        with mem_debug("my step description"):
            do_something()
    """
    if not LOGGER.isEnabledFor(logging.DEBUG):
        yield
        return

    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss
    peak_rss: list[int] = [mem_before]
    stop_event = threading.Event()

    def _sample() -> None:
        while not stop_event.is_set():
            peak_rss[0] = max(peak_rss[0], proc.memory_info().rss)
            stop_event.wait(sample_interval)

    sampler = threading.Thread(target=_sample, daemon=True)
    t0 = time.perf_counter()
    sampler.start()
    yield
    stop_event.set()
    sampler.join()
    elapsed = time.perf_counter() - t0
    mem_after = proc.memory_info().rss
    mem_before_mb = mem_before / 1e6
    mem_after_mb = mem_after / 1e6
    peak_mb = peak_rss[0] / 1e6
    warning = " [HIGH MEM]" if peak_mb >= MEMORY_WARNING_LIMIT else ""
    LOGGER.debug(
        "%-30s | start %7.1f MB | end %7.1f MB (%+.1f MB) | peak %7.1f MB (%+.1f MB) | %.3f s%s",
        label,
        mem_before_mb,
        mem_after_mb,
        mem_after_mb - mem_before_mb,
        peak_mb,
        peak_mb - mem_before_mb,
        elapsed,
        warning,
    )


def timeit(function: Callable[..., Any]) -> Any:
    """Meant to be used as a decorator using @timeit
    in order to measure the execution time of a function.

    Args:
        function (Callable[..., Any]): the function to measure exec time for.

    Returns:
        Any: the return of the function.
    """

    @wraps(function)
    def wrapper(*args: tuple[Any], **kwargs: dict[Any, Any]) -> Any:
        start_time = time.perf_counter()
        result = function(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        LOGGER.info('Function "%s" took %.4f seconds', function.__name__, total_time)

        return result

    return wrapper
