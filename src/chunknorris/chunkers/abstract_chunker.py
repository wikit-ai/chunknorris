from abc import ABC, abstractmethod
import json
import os
from typing import Any

from pydantic import validate_call

from .tools.tools import Chunk


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

    def save_chunks(
        self, chunks: list[Chunk], output_filename: str, remove_links: bool = False
    ) -> None:
        """Saves the chunks in .md files at the designated location.

        Args:
            chunks (Chunks): the chunks.
            output_filename (str): the JSON file where to save the files. Must be json.
            remove_links (bool): Whether or not links should be remove from the chunk's text content.
        """
        directory = os.path.dirname(os.path.abspath(output_filename))
        if not os.path.exists(directory):
            os.makedirs(directory)
        content = [
            {
                "text": chunk.get_text(remove_links=remove_links),
                "start_page": chunk.start_page,
                "end_page": chunk.end_page,
                "start_line": chunk.start_line,
            }
            for chunk in chunks
        ]
        with open(output_filename, "w", encoding="utf8") as f:
            json.dump(content, f, ensure_ascii=False)
