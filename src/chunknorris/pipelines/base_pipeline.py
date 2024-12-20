from chunknorris.chunkers.abstract_chunker import AbstractChunker
from chunknorris.parsers.abstract_parser import AbstractParser

from ..chunkers.tools.tools import Chunk
from .abstract_pipeline import AbstractPipeline


class BasePipeline(AbstractPipeline):
    def __init__(self, parser: AbstractParser, chunker: AbstractChunker) -> None:
        super().__init__(parser, chunker)

    def chunk_string(self, string: str) -> list[Chunk]:
        """Parses and chunks a string based on the provided
        parser and chunker.

        Args:
            string (str): a string.

        Returns:
            list[Chunk]: A list of chunks.
        """
        parsed_string = self.parser.parse_string(string)
        return self.chunker.chunk(parsed_string)

    def chunk_file(self, filepath: str) -> list[Chunk]:
        """Parses and chunks a string based on the provided
        parser and chunker.

        Args:
            filepath (Filepath): the path to a file.

        Returns:
            list[Chunk]: A list of chunks.
        """
        parsed_string = self.parser.parse_file(filepath)
        return self.chunker.chunk(content=parsed_string)
