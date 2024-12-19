import time
from functools import wraps
from inspect import signature
from typing import Any, Callable

from ..core.logger import LOGGER


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
