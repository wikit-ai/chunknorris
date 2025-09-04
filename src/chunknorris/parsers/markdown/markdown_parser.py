from pathlib import Path
import re
from typing import Any

import yaml

from ...core.components import MarkdownDoc
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
        formatted_string = MarkdownParser.cleanup_string(string)
        formatted_string, metadata = MarkdownParser.parse_metadata(formatted_string)
        formatted_string = MarkdownParser.convert_setext_to_atx(formatted_string)
        md_doc = MarkdownDoc.from_string(formatted_string)
        md_doc.metadata = metadata

        return md_doc

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

    @staticmethod
    def parse_metadata(md_string: str) -> tuple[str, dict[str, Any]]:
        """Parses the metadatas of a markdown string.
        Assumes the metadata are in YAML format, with '---' as first line.
        Example :
        ```md
        ---
        metakey : metavalue
        ---

        Content of document...
        ```
        Args:
            md_string (str): the string to get the metadata from

        Returns:
            str: the content of the docu, with the metadata section removed
            dict[str, Any]: the parsed metadata, as dict
        """
        if not md_string[:3] == "---":  # no metadata
            return md_string, {}
        # find idx of lines belonging to metadata
        lines = md_string.split("\n")
        try:
            end_idx = lines[1:].index("---") + 1
        except ValueError:
            return md_string, {}
        metadata = "\n".join(lines[1:end_idx]).strip()
        content = "\n".join(lines[end_idx + 1 :]).strip()
        try:
            metadata_as_json = yaml.safe_load(metadata) or {}
        except yaml.YAMLError:
            metadata_as_json = {}

        return content, metadata_as_json

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

        # remove base64 images
        pattern = r"data:image\/[bmp,gif,ico,jpg,png,svg,webp,x\-icon,svg+xml]+;base64,[a-zA-Z0-9,+,\/]+={0,2}"
        md_string = re.sub(pattern, "", md_string)

        return md_string
