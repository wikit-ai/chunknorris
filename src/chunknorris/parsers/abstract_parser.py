from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

InputT = TypeVar("InputT", str, bytes)


class AbstractParser(ABC, Generic[InputT]):
    """A parser is meant to parse either a string
    of a document provided as a file path.
    Either way, its output must be ingestable by a chunker.
    IMPORTANT : The types specified in the 2 abstract methods
    must be the same.
    """

    @abstractmethod
    def parse_string(self, string: InputT) -> Any:
        pass

    @abstractmethod
    def parse_file(self, filepath: str) -> Any:
        pass
