from __future__ import annotations
from unicodedata import normalize
from copy import deepcopy
import re
from typing import Optional
import json


class Chunk:
    headers: list[str]
    content: str
    start_line: int
    start_page: Optional[int]
    end_page: Optional[int]

    def __init__(
        self,
        headers: list[str],
        content: str,
        start_line: int,
        *,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
    ) -> None:
        self.headers = headers
        self.content = self._cleanup_text(content)
        self.start_line = start_line
        self.start_page = start_page
        self.end_page = end_page

    @property
    def word_count(self) -> int:
        return len(self.content.split())

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
        text = "\n\n".join(self.headers + [self.content])
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
    text: str
    level: int
    line_index: int
    content: str
    parent: TocTree | None
    children: list[TocTree]

    def __init__(
        self,
        *,
        title: str = "",
        children: list[TocTree] | None = None,
        content: str = "",
        id: int = -1,
        line_index: int = -1,
        level: int = -1,
        parent: TocTree | None = None,
    ) -> None:
        self.title = title
        self.content = content
        self.id = id
        self.line_index = line_index
        self.level = level
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
