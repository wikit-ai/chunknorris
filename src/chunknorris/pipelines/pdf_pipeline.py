from ..decorators.decorators import validate_args
from ..types.types import MarkdownString
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
        if not self.parser.toc:
            return False
        headers_found = [header for header in self.parser.toc if header.found]
        return len(headers_found) / len(self.parser.toc) > 0.5

    def chunk_with_headers(self) -> list[Chunk]:
        """Uses the MarkdownChunker to chunk the document
        based on headers.

        Returns:
            Chunks: the list of chunks
        """
        strings_per_page: dict[int, MarkdownString] = self.parser.to_markdown(
            keep_track_of_page=True
        )
        main_title = f"# {self.parser.main_title}\n\n" if self.parser.main_title else ""
        md_string = MarkdownString(
            content=main_title
            + "\n\n".join((string.content for string in strings_per_page.values()))
        )
        chunks = self.chunker.chunk_string(md_string)
        # build map dict[index of line : page_number] to keep track of the line index for each page
        # Add start line attribute
        line_to_page_map = {}
        line_idx = len(main_title.split("\n"))
        for page_n in sorted(strings_per_page.keys()):
            line_to_page_map[page_n] = line_idx
            line_idx += len(strings_per_page[page_n].content.split("\n"))
        for chunk in chunks:
            for page_n, line_idx in line_to_page_map.items():
                if line_idx < chunk.start_line:
                    chunk.start_page = page_n
        chunks[0].start_page = min(line_to_page_map.keys())
        # Add end line attribute
        for chunk, next_chunk in zip(chunks[:-1], chunks[1:]):
            chunk.end_page = next_chunk.start_page
        chunks[-1].end_page = list(strings_per_page.keys())[-1]

        return chunks

    def chunk_by_page(self) -> list[Chunk]:
        """Build one chunk per page.

        Returns:
            Chunks: the list of chunks.
        """
        strings_per_page: dict[int, MarkdownString] = self.parser.to_markdown(
            keep_track_of_page=True
        )
        main_title = f"# {self.parser.main_title}\n\n" if self.parser.main_title else ""

        chunks: list[Chunk] = []
        line_idx = 0
        for page_n, md_string in strings_per_page.items():
            chunks.append(
                Chunk(
                    headers=[main_title],
                    content=md_string.content,
                    start_page=page_n,
                    end_page=page_n + 1,
                    start_line=line_idx,
                )
            )
            line_idx += len(md_string.content.split("\n"))

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
