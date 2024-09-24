from abc import ABC, abstractmethod

from pydantic import validate_call

from ..types.types import AbstractInOutType


class AbstractParser(ABC):
    """A parser is meant to parse either a string
    of a document provided as a file path.
    Either way, it is expected to return a formatted
    string belonging to one of the option specified
    in TypeString.
    IMPORTANT : The types specified in the 3 abstract methods
    must be the same.
    """

    @validate_call
    @abstractmethod
    def parse_string(self, string: str) -> AbstractInOutType:
        pass

    @validate_call
    @abstractmethod
    def parse_file(self, filepath: str) -> AbstractInOutType:
        pass
