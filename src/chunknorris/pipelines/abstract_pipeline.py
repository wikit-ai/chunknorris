from abc import ABC, abstractmethod

from ..chunkers.abstract_chunker import AbstractChunker
from ..core.components import Chunk
from ..parsers.abstract_parser import AbstractParser


class AbstractPipeline(ABC):
    parser: AbstractParser
    chunker: AbstractChunker

    def __init__(self, parser: AbstractParser, chunker: AbstractChunker) -> None:
        self.parser = parser
        self.chunker = chunker

    @abstractmethod
    def chunk_string(self, string: str) -> list[Chunk]:
        """Given a string, returns a list of chunks.
        Leverages the provided chunker and parser.
        Might use self.parser.parse_string() and self.parser.parse_file()
        along with self.chunker.chunk().
        """
        pass

    @abstractmethod
    def chunk_file(self, filepath: str) -> list[Chunk]:
        """Given a filepath, returns a list of chunks.
        Leverages the provided chunker and parser.
        Might use self.parser.parse_string() and self.parser.parse_file()
        along with self.chunker.chunk_string().
        """
        pass

    def __call__(self, string: str) -> list[Chunk]:
        """Gets chunks a string

        Args:
            md_string (str): the markdown string

        Returns:
            Chunks: the list of chunk's texts
        """
        return self.chunk_string(string)

    def save_chunks(
        self, chunks: list[Chunk], output_filename: str, remove_links: bool = False
    ) -> None:
        """Saves the chunks at the designated location
        as a json list of chunks.

        Args:
            chunks (Chunks): the chunks.
            output_filename (str): the JSON file where to save the files. Must be json.
            remove_links (bool): Whether or not links should be remove from the chunk's text content.
        """
        self.chunker.save_chunks(chunks, output_filename, remove_links)
