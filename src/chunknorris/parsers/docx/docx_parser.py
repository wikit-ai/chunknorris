from pathlib import Path

import mammoth  # type: ignore : No stub files

from ...core.components import MarkdownDoc
from ..html.html_parser import HTMLParser


class DocxParser(HTMLParser):

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a HTML-formatted string.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            string (str): the markdown formatted string

        Returns:
            MarkdownDoc: the parsed document. Can be fed to chunker.
        """
        formatted_string = DocxParser.apply_markdownify(string)
        formatted_string = DocxParser.cleanup_string(formatted_string)

        return MarkdownDoc.from_string(formatted_string)

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Reads and parses a markdown-formatted string.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            filepath (FilePath): the path to a .html file

        Returns:
            MarkdownDoc: the parsed document. Can be fed to chunker.
        """
        html_string = DocxParser.read_file(filepath)

        return self.parse_string(html_string)

    @staticmethod
    def read_file(filepath: str) -> str:
        """Reads a Markdown file

        Args:
            filepath (str): the path to the HTML file.

        Returns:
            str: the HTML string.
        """
        path = Path(filepath)
        if path.suffix != ".docx":
            raise ValueError("Only .docx files can be passed to DocxParser.")
        with path.open("rb") as file:
            html_string = mammoth.convert_to_html(file).value  # type: ignore : Type of input is unknown

        return html_string
