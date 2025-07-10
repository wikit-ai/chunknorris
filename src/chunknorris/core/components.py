from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, computed_field


class MarkdownDoc(BaseModel):
    """A parsed Markdown Formatted-String,
    resulting in a list of MarkdownLine.
    Feats :
    - ATX header formatting.
    - Remove base64 images
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    content: list[MarkdownLine]
    metadata: dict[str, Any] = {}

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


class MarkdownLine(BaseModel):
    text: str = Field(description="the text content of the line")
    line_idx: int = Field(description="the index of the line in the markdown string")
    isin_code_block: bool = Field(
        description="whether or not the line belongs to a code block"
    )
    page: int | None = Field(
        description="the page the line belongs to (if markdown comes from converted paginated document)"
    )

    def __init__(
        self,
        text: str,
        line_idx: int,
        isin_code_block: bool = False,
        page: int | None = None,
        **kwargs: dict[str, Any],
    ) -> None:
        super().__init__(
            text=normalize("NFKD", text.strip()),
            line_idx=line_idx,
            isin_code_block=isin_code_block,
            page=page,
            **kwargs,
        )

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


class Chunk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    headers: list[MarkdownLine]
    content: list[MarkdownLine]
    start_line: int

    @computed_field
    @property
    def word_count(self) -> int:
        """Gets the amount of words in the chunk's content
        (headers not included)
        """
        text_content = "\n".join((line.text for line in self.content))
        return len(re.findall(r"\w+", Chunk._cleanup_text(text_content)))

    @computed_field
    @property
    def start_page(self) -> int | None:
        pages = [line.page for line in self.content if line.page is not None]
        if pages:
            return min(pages)
        else:
            return None

    @computed_field
    @property
    def end_page(self) -> int | None:
        pages = [line.page for line in self.content if line.page is not None]
        if pages:
            return max(pages)
        else:
            return None

    def __str__(self) -> str:
        return self.get_text()

    def get_text(self, remove_links: bool = False, prepend_headers: bool = True) -> str:
        """Gets the text of the chunk.

        Args:
            remove_links (bool, optional): If True, the markdown links will be removed (text of the link is kept).
                Defaults to False.

        Returns:
            str: the text
        """
        text = ""
        if prepend_headers:
            text += "\n\n".join((header.text for header in self.headers)) + "\n\n"
        text += "\n".join((line.text for line in self.content))
        if remove_links:
            text = Chunk.remove_links(text)

        return Chunk._cleanup_text(text)

    @staticmethod
    def remove_links(text: str) -> str:
        """Removes the markdown format of the links in the text.

        Args:
            text (str): the text to find the links in

        Returns:
            str: the formated text
        """
        pattern = r"\[?!?\[(.*?)\](\(.*\)\])?\((.*\..+?)(\s.*)?\)"
        matches = re.finditer(pattern, text)
        for match in matches:
            text = text.replace(match[0], match[1])

        return text

    @staticmethod
    def _cleanup_text(text: str) -> str:
        """Cleans up the text"""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        return text


class TocTree:
    id: int
    title: MarkdownLine
    content: list[MarkdownLine]
    parent: TocTree | None
    children: list[TocTree]

    def __init__(
        self,
        title: MarkdownLine,
        *,
        content: list[MarkdownLine] | None = None,
        children: list[TocTree] | None = None,
        id: int = -1,
        parent: TocTree | None = None,
    ) -> None:
        self.title = title
        self.content = [] if content is None else content
        self.id = id
        self.parent = parent
        self.children = [] if children is None else children

    def add_child(self, child: TocTree) -> None:
        """Adds a child to the list of TocTree.
        Self is added as parent

        Args:
            child (TocTree): a TocTree node to add to the children.
        """
        child.parent = self
        self.children.append(child)

    def get_title_by_id(self, id: int) -> TocTree | None:
        """Gets a toc tree using its id.

        Args:
            id (int): the id of the title we are looking for.

        Returns:
            TocTree: the element of title we were looking for
        """
        if self.id == id:
            return self
        for child in self.children:
            target = child.get_title_by_id(id)
            if target:
                return target

    def to_json(self, output_path: str = "./tree.json") -> None:
        """Outputs the tree as json.

        Returns:
            dict[str, Any]: the json
        """
        dumpable_tree = deepcopy(self)
        dumpable_tree.remove_circular_refs()
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(
                dumpable_tree,
                file,
                default=lambda o: o.__dict__,
                sort_keys=True,
                ensure_ascii=False,
                indent=4,
            )

    def remove_circular_refs(self):
        """Recursively removes the circular ref in dict
        (used to save as json).

        Args:
            tree (TocTree): a toc tree to remove circular refs
        """
        self.parent = None
        for child in self.children:
            child.remove_circular_refs()

    def get_text(self, content_only: bool = False) -> str:
        """Builds the text content of a toc tree

        Args:
            content_only (bool): if true, the text won't include headers, only content.

        Returns:
            str : the text content
        """
        text = "" if content_only else self.title.text + "\n\n"
        text += "\n".join((line.text for line in self.content))

        return text.strip()
