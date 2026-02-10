import re
from operator import attrgetter

from ....core.components import MarkdownDoc, MarkdownLine
from .utils import PdfParserState


class PdfExport(PdfParserState):
    """This class is intended to be inherited by the PdfParser.
    It groups all functions related to exporting the Pdf based
    on the elements parsed by the PdfParser. Uses attributes
    such as self.spans, self.lines and self.blocks
    """

    def to_markdown_doc(self) -> MarkdownDoc:
        """Generated the markdown doc to be fed in the
        MarkdownChunker.

        Returns:
            MarkdownDoc: the formatted markdown doc
        """
        items_to_export = sorted(self.blocks + self.tables, key=attrgetter("order"))
        md_lines: list[MarkdownLine] = []
        line_idx_counter = 0

        main_title = f"# {self.main_title}\n\n" if self.main_title else ""
        md_lines.append(MarkdownLine(text=main_title, line_idx=-1, page=0))

        for item in items_to_export:
            if item.is_header_footer:
                continue
            line_text = (
                "\n\n" + PdfExport._cleanup_md_string(item.to_markdown()) + "\n\n"
            )
            line_count = len(line_text.split("\n"))
            md_lines.append(
                MarkdownLine(
                    text=line_text,
                    line_idx=line_count,
                    isin_code_block=False,
                    page=item.page,
                )
            )
            line_idx_counter += line_count

        return MarkdownDoc(content=md_lines)

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

        return md_string.strip()
