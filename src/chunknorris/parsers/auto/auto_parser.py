from pathlib import Path

from ...parsers import (
    CSVParser,
    ExcelParser,
    HTMLParser,
    JupyterNotebookParser,
    MarkdownParser,
    PdfParser,
)
from ..abstract_parser import AbstractParser
from ..markdown.components import MarkdownDoc

# TODO : find method to browse trough module and build this automatically
# To avoid updating manually when new parsers are added
PARSER_TO_EXTENSIO_MAP = {
    PdfParser: [".pdf"],
    JupyterNotebookParser: [".ipynb"],
    CSVParser: [".csv"],
    MarkdownParser: [".md"],
    HTMLParser: [".html"],
    ExcelParser: [
        ".xls",
        ".xlsx",
        ".xlsm",
        ".xlsb",
        ".odf",
        ".ods",
        ".odt",
    ],
}


class AutoParser(AbstractParser):
    """Parser used to parse any file based on file extension using appropriate parser."""

    def __init__(self) -> None:
        pass  # Do we want to pass configs to the parsers ?

    @property
    def fileext_parser_mapping(self) -> dict[str, AbstractParser]:
        return {
            extension: parser
            for parser, extensions in PARSER_TO_EXTENSIO_MAP.items()
            for extension in extensions
        }

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Parses a file using appropriate parser

        Args:
            filepath (str): the path the file.

        Returns:
            MarkdownDoc: the parsed file.
        """
        path = Path(filepath)
        parser: AbstractParser | None = self.fileext_parser_mapping.get(
            path.suffix.lower(), None
        )
        if parser is None:
            raise ValueError(
                f"Parsing of '{path.suffix.lower()}' files is not available.\nFiles extensions compatible with AutoParser are : {list(self.fileext_parser_mapping.keys())}"
            )
        else:
            parser = parser()
            md_doc = parser.parse_file(filepath)  # TODO : fix typing error
            return md_doc

    def parse_string(self, string: str):
        return NotImplementedError(
            "Can't call AutoParser.parse_string(). Use the parser dedicated to your string type instead."
        )
