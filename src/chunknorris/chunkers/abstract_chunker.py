import json
import os
from abc import ABC, abstractmethod
from typing import Any

from ..core.components import Chunk


class AbstractChunker(ABC):

    @abstractmethod
    def chunk(self, content: Any) -> list[Chunk]:
        """Considering the output of a specified parser,
        must contain all the logic for chunking a string.

        Args:
            content (Any): the content to chunk. Might correspond to the
                output from the provided parser.

        Returns:
            list[Chunk]: A list of chunks
        """
        pass

    def __call__(self, string: Any) -> list[Chunk]:
        """Shortcut to call chunk() method."""
        return self.chunk(string)

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
            json.dump(content, f, ensure_ascii=False, indent=4)
