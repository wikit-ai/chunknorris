from itertools import groupby
from operator import attrgetter
from ..parsers.markdown.components import MarkdownLine
from ..decorators.decorators import validate_args
from ..chunkers.markdown_chunker import MarkdownChunker
from ..chunkers.tools.tools import Chunk
from ..parsers.pdf.pdf_parser import PdfParser


class PdfPipeline:
    """This pipeline is meant to be used on for pdf files.
    First, it uses a parser to parse the pdf to markdown format.
    Second, it build chunks based on headers if any have been found,
    or pages if not.
    """

    parser: PdfParser
    chunker: MarkdownChunker

    @validate_args
    def __init__(self, parser: PdfParser, chunker: MarkdownChunker) -> None:
        self.parser = parser
        self.chunker = chunker

    def chunk_string(
        self, string: bytes, page_start: int = 0, page_end: int | None = None
    ) -> list[Chunk]:
        """
        Chunks a PDF byte stream.
        It first convert the string to markdown using the PdfParser,
        and then chunks the markdown file.

        Args:
            filepath (str): the path to the pdf file to chunk
            page_start (int, optional): the page to start parsing from. Defaults to 0.
            page_end (int, optional): the page to stop parsing. None to parse until last page. Defaults to None.

        Returns:
            Chunks: the chunks
        """
        _ = self.parser.parse_string(string, page_start, page_end)
        return self._get_chunks_using_strategy()

    def chunk_file(
        self, filepath: str, page_start: int = 0, page_end: int | None = None
    ) -> list[Chunk]:
        """
        Chunks a PDF file.
        It first convert the pdf file to markdown using the PdfParser,
        and then chunks the markdown file.

        Args:
            filepath (str): the path to the pdf file to chunk
            page_start (int, optional): the page to start parsing from. Defaults to 0.
            page_end (int, optional): the page to stop parsing. None to parse until last page. Defaults to None.

        Returns:
            Chunks: the chunks
        """
        _ = self.parser.parse_file(filepath, page_start, page_end)
        return self._get_chunks_using_strategy()

    def _get_chunks_using_strategy(self) -> list[Chunk]:
        """Handles the routing toward the adequate chunking
        strategy.
        The chunking strategy is as follow :
        - if table of content found in document -> chunk based on table of content
        - if not -> chunk by page

        Returns:
            Chunk: the list of chunks
        """
        doc_orientation = self.parser.get_document_orientation()

        if self.headers_have_been_found():
            chunks = self.chunk_with_headers()
        elif doc_orientation == "landscape":
            chunks = self.chunk_by_page()
        # placeholder : if no headers found and document is portrait, then chunk with headers
        # as no header have been found, this will result in on big chunk being chunk into subchunks by word length
        # In the future, a method will be implemented to detect TOC using advanced techniques.
        else:
            chunks = self.chunk_with_headers()

        self.parser.cleanup_memory()

        return chunks

    def headers_have_been_found(self) -> bool:
        """Determines whether or not enough header have been
        found in order to chunk document using MarkdownChunker.
        If more than half the headers have been found, returns True.

        Returns:
            bool : True if detected headers have been found in document.
        """
        if len(self.parser.toc) < 3:
            return False
        headers_found = [header for header in self.parser.toc if header.found]
        return len(headers_found) / len(self.parser.toc) > 0.5

    def chunk_with_headers(self) -> list[Chunk]:
        """Uses the MarkdownChunker to chunk the document
        based on headers.

        Returns:
            Chunks: the list of chunks
        """
        main_title = f"# {self.parser.main_title}\n\n" if self.parser.main_title else ""
        md_doc = self.parser.to_markdown_doc()
        md_doc.content.insert(0, MarkdownLine(text=main_title, line_idx=-1, page=0))
        chunks = self.chunker.chunk(md_doc)

        return chunks

    def chunk_by_page(self) -> list[Chunk]:
        """Build one chunk per page.

        Returns:
            Chunks: the list of chunks.
        """
        main_title = f"# {self.parser.main_title}\n\n" if self.parser.main_title else ""
        md_doc = self.parser.to_markdown_doc()
        lines_per_page: dict[int, list[MarkdownLine]] = {
            page: list(lines)
            for page, lines in groupby(md_doc.content, key=attrgetter("page"))
        }

        chunks: list[Chunk] = []
        line_idx = 0
        for lines in lines_per_page.values():
            chunks.append(
                Chunk(
                    headers=[MarkdownLine(text=main_title, line_idx=-1, page=0)],
                    content=lines,
                    start_line=line_idx,
                )
            )
            line_idx += len("\n".join((line.text for line in lines)).split("\n"))

        chunks = self.chunker.split_big_chunks(chunks)

        return chunks

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
