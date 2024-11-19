from __future__ import annotations
from unicodedata import normalize
from copy import deepcopy
import re
import json

from ...parsers.markdown.components import MarkdownLine


class Chunk:
    headers: list[MarkdownLine]
    content: list[MarkdownLine]
    start_line: int

    def __init__(
        self,
        headers: list[MarkdownLine],
        content: list[MarkdownLine],
        start_line: int,
    ) -> None:
        self.headers = headers
        self.content = content
        self.start_line = start_line

    @property
    def word_count(self) -> int:
        """Gets the amount of words in the chunk's content
        (headers not included)
        """
        text_content = "\n".join((line.text for line in self.content))
        return len(Chunk._cleanup_text(text_content).split())

    @property
    def start_page(self) -> int | None:
        pages = [line.page for line in self.content if line.page is not None]
        if pages:
            return min(pages)
        else:
            return None

    @property
    def end_page(self) -> int | None:
        pages = [line.page for line in self.content if line.page is not None]
        if pages:
            return max(pages)
        else:
            return None

    def __str__(self) -> str:
        return self.get_text()

    def get_text(self, remove_links: bool = False) -> str:
        """Gets the text of the chunk.

        Args:
            remove_links (bool, optional): If True, the markdown links will be removed (text of the link is kept).
                Defaults to False.

        Returns:
            str: the text
        """
        text = "\n\n".join((header.text for header in self.headers))
        text += "\n\n" + "\n".join((line.text for line in self.content))
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
        text = normalize("NFKD", text)
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
