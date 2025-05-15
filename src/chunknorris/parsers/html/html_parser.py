import re
from pathlib import Path

from ...core.components import MarkdownDoc
from ...core.custom_markdownify import (
    CustomMarkdownConverter,
)  # type: ignore : no stub file
from ..abstract_parser import AbstractParser


class HTMLParser(AbstractParser):

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a markdown-formatted string.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            string (str): the markdown formatted string

        Returns:
            MarkdownDoc: the parsed document. Can be fed to chunker.
        """
        formatted_string = HTMLParser.apply_markdownify(string)
        formatted_string = HTMLParser.cleanup_string(formatted_string)

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
        html_string = HTMLParser.read_file(filepath)

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
        if path.suffix != ".html":
            raise ValueError("Only .html files can be passed to HTMLParser.")
        with path.open("r", encoding="utf8") as file:
            html_string = file.read()

        return html_string

    @staticmethod
    def apply_markdownify(html_string: str) -> str:
        """Applies markdownify to the html text

        Args:
            html_string (str): an HTML-formatted string.

        Returns:
            str: the markdownified string.
        """
        md_string = html_string
        initial_len, new_len = len(md_string), 0
        while new_len < initial_len:
            initial_len = len(md_string)
            md_string = CustomMarkdownConverter(
                heading_style="ATX",
                strip=["figure", "img"],
                bullets="-*+",
                escape_asterisks=False,
                escape_underscores=False,
                escape_misc=False,
            ).convert(  # type: ignore MarkdownConverter.convert()->str
                md_string
            )
            new_len = len(md_string)

        md_string = "\n".join(
            line + "\n" if line.startswith("#") else line
            for line in str(md_string).split("\n")
        )

        return md_string

    @staticmethod
    def cleanup_string(md_string: str) -> str:
        """Cleans up the html string.

        Args:
            md_string (str): the markdown string, output from
                apply_markdownify()

        Returns:
            str: the cleaned up string.
        """
        md_string = md_string.strip()
        md_string = re.sub(r"(?:\n\s*){3,}", "\n\n", md_string)

        return md_string
