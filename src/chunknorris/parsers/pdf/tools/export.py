import os
import re
from operator import attrgetter
from itertools import groupby

from ....types.types import MarkdownString
from .utils import PdfParserState


class PdfExport(PdfParserState):
    """This class is intended to be inherited by the PdfParser.
    It groups all functions related to exporting the Pdf based
    on the elements parsed by the PdfParser. Uses attributes
    such as self.spans, self.lines and self.blocks
    """

    def to_markdown(
        self,
        keep_track_of_page: bool = False,
    ) -> MarkdownString | dict[int, MarkdownString]:
        """Export parsed content to markdown.

        Args:
            keep_track_of_page (bool) : if True, returns a dict with
                dict[page_number : MarkdownString]. Page number is 1-based
                and page 0 is reserved for main document title.
                If False returns a string for the whole document.
                Defaults to False.

        Returns:
            str | list[str]: the markdown string of the specified page range.
        """
        blocks_by_page = {
            page: list(blocks)
            for page, blocks in groupby(self.blocks, key=attrgetter("page"))
        }
        tables_by_page = {
            page: list(blocks)
            for page, blocks in groupby(self.tables, key=attrgetter("page"))
        }

        prefix = f"# {self.main_title}\n\n" if self.main_title else ""
        string_per_page = {}

        for page_n in range(self.page_start, self.page_end):
            blocks_on_page = blocks_by_page[page_n] if page_n in blocks_by_page else []
            tables_on_page = tables_by_page[page_n] if page_n in tables_by_page else []
            items_to_export = sorted(
                blocks_on_page + tables_on_page, key=attrgetter("order")
            )
            md_string = "\n\n".join(item.to_markdown() for item in items_to_export)
            md_string = PdfExport._cleanup_md_string(md_string)
            string_per_page[page_n + 1] = md_string.strip()

        if keep_track_of_page:
            return {
                page_n: MarkdownString(content=md_string)
                for page_n, md_string in string_per_page.items()
            }

        return MarkdownString(content=prefix + "\n\n".join(string_per_page.values()))

    @staticmethod
    def _cleanup_md_string(md_string: str) -> str:
        """Performs various cleanup operation
        of the markwdown string output by to_markdown()

        Args:
            md_string (str): the markdown string

        Returns:
            str : the cleaned up string
        """
        md_string = re.sub(r"\*\* *\*\*", " ", md_string)
        md_string = md_string.replace(" ** ", "**\n")
        md_string = re.sub(r"\n{3,}", "\n\n", md_string)

        return md_string

    def save_markdown(self, output_filepath: str = "./output.md") -> None:
        """Generates the markdown export of the pdf
        and saves it in a file

        Args:
            output_filpath (str): the file path where the md is saved
        """
        md_string = self.to_markdown()
        if not os.path.exists(os.path.dirname(output_filepath)):
            os.makedirs(os.path.dirname(output_filepath))
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(md_string)

    def to_text(self) -> str:
        """
        Converts the parsed document to a text string
        without formatting

        Returns:
            str: the raw text string
        """
        raise NotImplementedError()
