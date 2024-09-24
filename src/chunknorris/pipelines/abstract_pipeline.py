from abc import ABC, abstractmethod
import json
import os
from ..chunkers.abstract_chunker import AbstractChunker
from ..chunkers.tools import Chunk
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
        along with self.chunker.chunk_string().
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

    def save_chunks_as_json(
        self, chunks: list[Chunk], out_filepath: str | None = None
    ) -> None:
        """Saves the chunks at the designated location
        as a json list of chunks.

        Args:
            chunks (Any): the content of the file to write
            out_filepath (FilePath): path of the output. Must end with json.
        """
        if out_filepath is None:
            out_filepath = "chunks.json"
        if not out_filepath.endswith(".json"):
            raise ValueError("The provided output filepath must end with '.json'.")
        dir_name = os.path.dirname(out_filepath)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        dumpable_chunks = [
            {
                "text": chunk.get_text(),
                "start_line": chunk.start_line,
                "start_page": chunk.start_page,
                "end_page": chunk.end_page,
            }
            for chunk in chunks
        ]
        with open(out_filepath, "w", encoding="utf-8") as file:
            json.dump(dumpable_chunks, file)
