from abc import ABC, abstractmethod
from typing import Any

from pydantic import validate_call


class AbstractParser(ABC):
    """A parser is meant to parse either a string
    of a document provided as a file path.
    Either way, its output must be ingestable by a chunker.
    IMPORTANT : The types specified in the 2 abstract methods
    must be the same.
    """

    @validate_call
    @abstractmethod
    def parse_string(self, string: str) -> Any:
        pass

    @validate_call
    @abstractmethod
    def parse_file(self, filepath: str) -> Any:
        pass
