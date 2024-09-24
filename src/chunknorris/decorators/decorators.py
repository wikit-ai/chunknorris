from inspect import signature
from typing import Any, Callable


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
