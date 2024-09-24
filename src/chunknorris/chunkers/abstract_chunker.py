from abc import ABC, abstractmethod
from typing import Any

from pydantic import validate_call

from .tools import Chunk


class AbstractChunker(ABC):

    @validate_call
    @abstractmethod
    def chunk_string(self, string: Any) -> list[Chunk]:
        """Considering the output of a specified parser,
        must contain all the logic for parsing a string.

        One might use the output of the parser: string.content

        Args:
            string (Any): the string output from the
                provided parser. Can be any type that inherits
                AbstractInOutType.

        Returns:
            list[Chunk]: A list of chunks
        """
        pass

    def __call__(self, string: Any) -> list[Chunk]:
        """Shortcut to call chunk_string() method."""
        return self.chunk_string(string)
