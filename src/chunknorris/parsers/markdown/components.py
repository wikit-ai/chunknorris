from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class MarkdownDoc(BaseModel):
    """A parsed Markdown Formatted-String,
    resulting in a list of MarkdownLine.
    Feats :
    - ATX header formatting.
    - Remove base64 images
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    content: list[MarkdownLine]

    def to_string(self) -> str:
        """Get the markdown string corresponding to the document's content"""
        return "\n".join(line.text for line in self.content)

    @staticmethod
    def from_string(md_string: str) -> MarkdownDoc:
        """Get the MardownDoc object from
        a markdown formatted string.

        Args:
            md_string (str): the markdown string

        Returns:
            MarkdownDoc: the markdown document
        """
        within_code_block = False
        md_lines: list[MarkdownLine] = []

        for i, line in enumerate(md_string.split("\n")):
            if line.startswith("```") and "```" not in line[3:]:
                within_code_block = not within_code_block
            md_lines.append(
                MarkdownLine(
                    text=line,
                    line_idx=i,
                    isin_code_block=(line == "```") or within_code_block,
                )
            )

        return MarkdownDoc(content=md_lines)


class MarkdownLine:
    text: str  # the text content of the line
    order: int  # the order of the line in the markdown string
    isin_code_block: bool  # whether or not the line belongs to a code block
    page: int | None  # the page the line belongs to (for pdf to markdown conversion)

    def __init__(
        self,
        text: str,
        line_idx: int,
        isin_code_block: bool = False,
        page: int | None = None,
    ) -> None:
        self.text = text.strip()
        self.line_idx = line_idx
        self.isin_code_block = isin_code_block
        self.page = page

    @property
    def isin_table(self) -> bool:
        """whether or not the line belongs to a table"""
        return self.text.startswith("|")

    @property
    def is_header(self):
        return self.text.lstrip("- ").startswith("#") and not self.isin_code_block

    @property
    def is_bullet_point(self) -> bool:
        "whether or not the line is a bullet point"
        return self.text.startswith("- ")

    def get_header_level(self) -> int:
        """Gets the header level of this line (1-based)

        Raises:
            ValueError: if the line is not a header, raises an error

        Returns:
            int: the header level, h1 headers would return 1
        """
        if not self.is_header:
            raise ValueError("No header level as this line is not a header")
        else:
            text = self.text.lstrip("- ")
            return min(len(text) - len(text.lstrip("#")), 6)

    def __str__(self):
        return str(vars(self))
