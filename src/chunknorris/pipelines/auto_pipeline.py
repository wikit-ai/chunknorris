from ..chunkers.markdown_chunker import MarkdownChunker
from ..chunkers.tools.tools import Chunk
from ..parsers.auto.auto_parser import AutoParser
from ..parsers.pdf.pdf_parser import PdfParser
from .abstract_pipeline import AbstractPipeline
from .base_pipeline import BasePipeline
from .pdf_pipeline import PdfPipeline


class AutoPipeline(AbstractPipeline):
    def __init__(self) -> None:
        pass

    def chunk_string(self, string: str) -> list[Chunk]:
        """Parses and chunks a string based on the provided
        parser and chunker.

        Args:
            string (str): a string.

        Returns:
            list[Chunk]: A list of chunks.
        """
        return NotImplementedError(
            "Can't call AutoPipeline.chunk_string(). Use the parser dedicated to your string type instead."
        )

    def chunk_file(self, filepath: str) -> list[Chunk]:
        """Parses and chunks a string based on the provided
        parser and chunker.

        Args:
            filepath (Filepath): the path to a file.

        Returns:
            list[Chunk]: A list of chunks.
        """
        if filepath.lower().endswith(".pdf"):
            pipe = PdfPipeline(PdfParser(), MarkdownChunker())
        else:
            pipe = BasePipeline(AutoParser(), MarkdownChunker())

        return pipe.chunk_file(filepath)
