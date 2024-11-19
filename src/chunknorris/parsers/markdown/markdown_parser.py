from pathlib import Path

from .components import MarkdownDoc
from ..abstract_parser import AbstractParser


class MarkdownParser(AbstractParser):

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a markdown-formatted string.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            string (str): the markdown formatted string

        Returns:
            TypedString: the formatted markdown string
        """
        formatted_string = MarkdownParser.convert_setext_to_atx(string)

        return MarkdownDoc.from_string(formatted_string)

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Reads and parses a markdown-formatted string.
        Ensures that the formatting is suited to be passed
        to the MarkdownChunker.

        Args:
            filepath (FilePath): the path to a .md file

        Returns:
            TypedString: the typed string
        """
        md_string = MarkdownParser.read_file(filepath)

        return self.parse_string(md_string)

    @staticmethod
    def read_file(filepath: str) -> str:
        """Reads a Markdown file

        Args:
            filepath (str): the path to the markdown file

        Returns:
            str: the markdown string
        """
        path = Path(filepath)
        if path.suffix != ".md":
            raise ValueError("Only .md files can be passed to MarkDownParser.")
        with path.open("r", encoding="utf8") as file:
            md_string = file.read()

        return md_string

    @staticmethod
    def convert_setext_to_atx(md_string: str) -> str:
        """Converts headers from setext style to atx style

        Args:
            md_string (str): the markdown string

        Return:
            str: the string with formatted headers
        """
        output_lines: list[str] = []
        within_code_block = False
        prev_line = ""

        for line in md_string.split("\n"):
            if line.startswith("```") and "```" not in line[3:]:
                within_code_block = not within_code_block
            if not within_code_block:
                if line.startswith("==="):
                    output_lines.pop()
                    output_lines.append(f"# {prev_line}")
                elif line.startswith("---"):
                    output_lines.pop()
                    output_lines.append(f"## {prev_line}")
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)
            prev_line = line

        return "\n".join(output_lines)
