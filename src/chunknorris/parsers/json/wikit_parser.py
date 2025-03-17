import json
from pathlib import Path

from pydantic import ValidationError

from ...core.components import MarkdownDoc
from ...parsers.html.html_parser import HTMLParser
from ...parsers.markdown.markdown_parser import MarkdownParser
from ...schemas.schemas import WikitJSONDocument
from ..abstract_parser import AbstractParser


class WikitJsonParser(AbstractParser):
    """This parser is intended to be used on
    the JSON files that are formatted according
    to the WikitJSONDocument interface.
    """

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a json string.

        Args:
            string (str): a json string.

        Returns:
            MarkdownDoc : the formatted markdown string.
        """
        try:
            content = json.loads(string)
            content = WikitJSONDocument(**content)
        except (json.JSONDecodeError, ValidationError) as e:
            raise e

        return self.parse_wikit_json_document(content)

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Parses a json file formatted according to Wikit's schema.

        Args:
            filepath (FilePath): the path to a file.

        Returns:
            MarkdownDoc: the formatted markdown string.
        """
        content = self.read_file(filepath)

        return self.parse_wikit_json_document(content)

    def parse_wikit_json_document(self, content: WikitJSONDocument) -> MarkdownDoc:
        """Parses the has_part key json document
        according to the specified text format.

        Args:
            content (WikitJSONDocument): the content to be parsed.

        Returns:
            MarkdownDoc: the formatted markdown string.
        """
        has_part = content.has_part[0].text
        match content.file_format:
            case None:
                raise ValueError(
                    "No value under 'file_format' key. File format must be specified."
                )
            case "text/markdown":
                parser = MarkdownParser()
            case "text/html":
                parser = HTMLParser()
            case other:
                raise ValueError(
                    f"Only text/markdown and text/html are handle by WikitJsonParser. Got {other}."
                )

        return parser.parse_string(has_part)

    def read_file(self, filepath: str) -> WikitJSONDocument:
        """Reads a Markdown file

        Args:
            filepath (str): the path to the markdown file

        Returns:
            str: the markdown string
        """
        path = Path(filepath)
        if path.suffix != ".json":
            raise ValueError("Only .json files can be passed to WikitJsonParser.")
        with path.open("r", encoding="utf8") as file:
            content = json.load(file)
        try:
            content = WikitJSONDocument(**content)
        except ValidationError as e:
            raise e

        return content
