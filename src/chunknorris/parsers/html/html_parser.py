import re
from pathlib import Path

from ...core.components import MarkdownDoc
from ...core.custom_markdownify import (
    CustomMarkdownConverter,
)  # type: ignore : no stub file
from ..abstract_parser import AbstractParser

_RE_BLANK_LINES = re.compile(r"(?:\n\s*){3,}")
_RE_BASE64_IMAGE = re.compile(
    r"data:image/(?:bmp|gif|ico|jpg|jpeg|png|svg|webp|x-icon|svg\+xml);base64,[a-zA-Z0-9+/]+=*"
)
_MARKDOWNIFY_OPTIONS: dict = {
    "autolinks": False,
    "heading_style": "ATX",
    "strip": ["figure", "img"],
    "bullets": "-*+",
    "escape_asterisks": False,
    "escape_underscores": False,
    "escape_misc": False,
}


class HTMLParser(AbstractParser[str]):

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses an HTML-formatted string.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            string (str): the HTML formatted string

        Returns:
            MarkdownDoc: the parsed document. Can be fed to chunker.
        """
        formatted_string = HTMLParser.apply_markdownify(string)
        formatted_string = HTMLParser.cleanup_string(formatted_string)

        return MarkdownDoc.from_string(formatted_string)

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Reads and parses an HTML file.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            filepath (str): the path to a .html or .htm file

        Returns:
            MarkdownDoc: the parsed document. Can be fed to chunker.
        """
        html_string = HTMLParser.read_file(filepath)

        return self.parse_string(html_string)

    @staticmethod
    def read_file(filepath: str) -> str:
        """Reads an HTML file.

        Args:
            filepath (str): the path to the HTML file.

        Returns:
            str: the HTML string.
        """
        path = Path(filepath)
        if path.suffix not in {".html", ".htm"}:
            raise ValueError("Only .html / .htm files can be passed to HTMLParser.")
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")
        with path.open("r", encoding="utf8") as file:
            return file.read()

    @staticmethod
    def apply_markdownify(html_string: str) -> str:
        """Applies markdownify to the HTML string, iterating until the output
        stabilises (handles nested HTML structures such as tables within tables).

        Args:
            html_string (str): an HTML-formatted string.

        Returns:
            str: the markdownified string.
        """
        converter = CustomMarkdownConverter(**_MARKDOWNIFY_OPTIONS)
        md_string = html_string
        while True:
            converted = converter.convert(md_string)  # type: ignore MarkdownConverter.convert()->str
            if converted == md_string:
                break
            md_string = converted

        # Add a blank line after each heading so downstream parsing is unambiguous.
        md_string = re.sub(r"(^#{1,6} .+)$", r"\1\n", md_string, flags=re.MULTILINE)

        return md_string

    @staticmethod
    def cleanup_string(md_string: str) -> str:
        """Cleans up the markdownified string.

        Args:
            md_string (str): the markdown string, output from apply_markdownify().

        Returns:
            str: the cleaned up string.
        """
        md_string = md_string.strip()
        md_string = _RE_BLANK_LINES.sub("\n\n", md_string)
        md_string = _RE_BASE64_IMAGE.sub("", md_string)

        return md_string
