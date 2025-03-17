from ..core.components import Chunk
from .abstract_pipeline import AbstractPipeline


class BasePipeline(AbstractPipeline):

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
        return self.chunker.chunk(parsed_string)
