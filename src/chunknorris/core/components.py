from __future__ import annotations

import json
import os
import re
import warnings
from copy import deepcopy
from typing import Any, Iterator, Literal, overload
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field

# Markdown image reference, such as ![alt](target)
_RE_IMAGE_REF = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
# Same, but also capturing the alt text: (alt, target)
_RE_IMAGE_FULL = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
# Bullet or numbered list marker, such as "- " or "1. "
_RE_LIST_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s+")


def _get_block_kind(line: MarkdownLine, edge: Literal["start", "end"]) -> str | None:
    """Gets the kind of markdown block (table or blockquote) that requires to be
    isolated by blank lines, at the start or at the end of the line, if any.
    A line may span several rows, such as an image followed by its caption
    as a blockquote: it starts as an image but ends as a blockquote."""
    if line.isin_code_block:
        return None
    rows = line.text.split("\n")
    row = rows[0] if edge == "start" else rows[-1]
    if row.startswith("|"):
        return "table"
    if row.startswith(">"):
        return "blockquote"
    return None


def _is_caption_of(line: MarkdownLine, prev: MarkdownLine) -> bool:
    """Whether the line is the caption (blockquote) of the image ending the previous line."""
    return (
        _get_block_kind(line, "start") == "blockquote"
        and _RE_IMAGE_REF.fullmatch(prev.text.split("\n")[-1]) is not None
    )


def _join_lines(lines: list[MarkdownLine], isolate_headers: bool = True) -> str:
    """Joins the lines in a markdown string. Tables and blockquotes (and headers,
    if isolate_headers) are separated from the surrounding content by a blank line,
    otherwise markdown viewers would merge the following paragraph into them.
    The caption of an image is kept right under it."""
    parts: list[str] = []
    prev: MarkdownLine | None = None
    for line in lines:
        text = f"\n{line.text}\n" if isolate_headers and line.is_header else line.text
        if (
            prev is not None
            and prev.text
            and line.text
            and _get_block_kind(prev, "end") != _get_block_kind(line, "start")
            and not _is_caption_of(line, prev)
        ):
            text = f"\n{text}"
        parts.append(text)
        prev = line
    return "\n".join(parts)


def _cleanup_text(text: str) -> str:
    """Cleans up the text"""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def _remove_links(text: str) -> str:
    """Removes the markdown format of the links in the text (text of the link is kept)."""
    pattern = r"\[?!?\[(.*?)\](\(.*\)\])?\((.*\..+?)(\s.*)?\)"
    return re.sub(pattern, r"\1", text)


def _render(
    lines: list[MarkdownLine],
    images: dict[str, DocImage],
    include_images: bool = False,
    remove_links: bool = False,
) -> str:
    """Builds the markdown string of the lines. Images are isolated by blank lines,
    and embedded as base64 definitions if required."""
    used: dict[str, str] = {}

    def _isolate(match: re.Match[str]) -> str:
        alt, image_id = match.groups()
        image = images.get(image_id)
        ref = match.group(0)
        if include_images and image is not None and image.base64:
            used[image_id] = image.base64
            ref = f"![{alt}][{image_id}]"
        # isolating an image that opens a list item would break the list
        line_start = match.string.rfind("\n", 0, match.start()) + 1
        if _RE_LIST_MARKER.fullmatch(match.string, line_start, match.start()):
            return ref
        # keep the caption (blockquote) attached to its image
        after = "" if match.string.startswith("\n>", match.end()) else "\n\n"
        return f"\n\n{ref}{after}"

    text = _RE_IMAGE_FULL.sub(_isolate, _join_lines(lines))
    if remove_links:
        # embedded images are reference-style (![alt][id]), so they are kept
        text = _remove_links(text)
    text = _cleanup_text(text)
    if not used:
        return text
    definitions = "\n".join(f"[{id_}]: {data}" for id_, data in used.items())
    return f"{text}\n\n{definitions}"


class DocImage(BaseModel):
    """An image of a document, referenced in the markdown as ![...](id)."""

    id: str = Field(
        description="the identifier of the image, used as link target in the markdown"
    )
    page: int | None = Field(
        default=None, description="the page the image belongs to (0-based)"
    )
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description="the location of the image on the page (x0, y0, x1, y1), in PDF points",
    )
    image_type: str | None = Field(
        default=None,
        description="the category of the image (chart, screenshot, signature...)",
    )
    caption: str | None = Field(
        default=None, description="a textual description of the image"
    )
    base64: str | None = Field(
        default=None, description="the image, as a base64 encoded data URI"
    )


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
    images: dict[str, DocImage] = {}

    @overload
    def to_string(
        self,
        keep_track_of_page: Literal[False] = False,
        include_images: bool = False,
    ) -> str: ...

    @overload
    def to_string(
        self, keep_track_of_page: Literal[True], include_images: bool = False
    ) -> dict[int | None, str]: ...

    def to_string(
        self, keep_track_of_page: bool = False, include_images: bool = False
    ) -> str | dict[int | None, str]:
        """Get the markdown string corresponding to the document's content

        Args:
            keep_track_of_page (bool): if True, returns a dict as {page_number : string}.
                Page number is 0-based. For non paginated documents, returns {None: entire document string}
                If False returns a string for the whole document.
                Defaults to False.
            include_images (bool): if True, the images that have base64 data are embedded.
                To keep the text readable, references are rewritten as ![alt][id] and
                the data URIs are appended as definitions ([id]: data:...) at the end
                of the string (of each page if keep_track_of_page).
                Defaults to False."""
        if keep_track_of_page:
            lines_per_page: dict[int | None, list[MarkdownLine]] = {}
            for line in self.content:
                lines_per_page.setdefault(line.page, []).append(line)
            return {
                page: _render(lines, self.images, include_images)
                for page, lines in lines_per_page.items()
            }

        return _render(self.content, self.images, include_images)

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

    def save(self, output_filepath: str = "./output.md") -> None:
        """Saves the markdown export of the document in a file.

        Args:
            output_filpath (str): the file path where the md is saved
        """
        md_string = self.to_string()
        if not os.path.exists(os.path.dirname(output_filepath)):
            os.makedirs(os.path.dirname(output_filepath))
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(md_string)


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
            text=normalize("NFKC", text.strip()),
            line_idx=line_idx,
            isin_code_block=isin_code_block,
            page=page,
            **kwargs,
        )

    @property
    def isin_table(self) -> bool:
        """whether or not the line belongs to a table"""
        return self.text.startswith("|") or self.text.startswith("<table>")

    @property
    def is_header(self) -> bool:
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
    images: dict[str, DocImage] = {}
    _word_count_cache: int | None = PrivateAttr(default=None)

    @computed_field
    @property
    def word_count(self) -> int:
        """Gets the amount of words in the chunk's content
        (headers not included)
        """
        if self._word_count_cache is None:
            text_content = "\n".join(line.text for line in self.content)
            self._word_count_cache = len(
                re.findall(r"\w+", _cleanup_text(text_content))
            )
        return self._word_count_cache

    @computed_field
    @property
    def start_page(self) -> int | None:
        return min(
            (line.page for line in self.content if line.page is not None), default=None
        )

    @computed_field
    @property
    def end_page(self) -> int | None:
        return max(
            (line.page for line in self.content if line.page is not None), default=None
        )

    def __str__(self) -> str:
        return self.to_string()

    def get_image_ids(self) -> list[str]:
        """Gets the ids of the images referenced in the chunk,
        such as "img-0.jpeg" for ![chart](img-0.jpeg).

        Returns:
            list[str]: the ids of the images, in order of appearance.
        """
        return list(
            dict.fromkeys(
                image_id
                for line in self.headers + self.content
                for image_id in _RE_IMAGE_REF.findall(line.text)
            )
        )

    def to_string(
        self,
        remove_links: bool = False,
        prepend_headers: bool = True,
        include_images: bool = False,
    ) -> str:
        """Gets the markdown string of the chunk.

        Args:
            remove_links (bool, optional): If True, the markdown links will be removed (text of the link is kept).
                Defaults to False.
            prepend_headers (bool, optional): If True, the headers of the parent sections
                are prepended to the chunk's content. Defaults to True.
            include_images (bool, optional): if True, the images that have base64 data are embedded.
                To keep the text readable, references are rewritten as ![alt][id] and
                the data URIs are appended as definitions ([id]: data:...) at the end of the string.
                Defaults to False.

        Returns:
            str: the text
        """
        lines = self.headers + self.content if prepend_headers else self.content
        return _render(lines, self.images, include_images, remove_links)

    def get_text(self, remove_links: bool = False, prepend_headers: bool = True) -> str:
        """Deprecated: use Chunk.to_string() instead."""
        warnings.warn(
            "Chunk.get_text() is deprecated, use Chunk.to_string() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.to_string(
            remove_links=remove_links, prepend_headers=prepend_headers
        )

    @staticmethod
    def remove_links(text: str) -> str:
        """Removes the markdown format of the links in the text.

        Args:
            text (str): the text to find the links in

        Returns:
            str: the formated text
        """
        return _remove_links(text)


class TocTree:
    id: int
    title: MarkdownLine
    content: list[MarkdownLine]
    parent: TocTree | None
    children: list[TocTree]
    _word_count_cache: int | None

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
        self._word_count_cache = None

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

    def get_parent_headers(self) -> list[MarkdownLine]:
        """Gets the list of ancestor header lines, ordered outermost to innermost.

        Returns:
            list[MarkdownLine]: ancestor titles, empty-title root excluded.
        """
        headers: list[MarkdownLine] = []
        node = self
        while node.parent:
            node = node.parent
            headers.append(node.title)
        return list(reversed([h for h in headers if h.text]))

    def estimate_word_count(self) -> int:
        """Estimates the total word count of this section (title + content + all descendants).
        Uses whitespace splitting — intentionally approximate for threshold checks.
        Result is cached since the tree is not modified during chunking.
        """
        if self._word_count_cache is not None:
            return self._word_count_cache
        count = len(self.title.text.split()) + sum(
            len(line.text.split()) for line in self.content
        )
        for child in self.children:
            count += child.estimate_word_count()
        self._word_count_cache = count
        return count

    def iter_content_lines(self) -> Iterator[MarkdownLine]:
        """Yields all lines in this section: title, content, then children recursively."""
        yield self.title
        yield from self.content
        for child in self.children:
            yield from child.iter_content_lines()

    def to_chunk(self, parent_headers: list[MarkdownLine] | None = None) -> Chunk:
        """Builds a Chunk from this TocTree element.

        Args:
            parent_headers: ancestor header lines. If None, derived by traversing the parent chain.

        Returns:
            Chunk: the chunk for this section.
        """
        if parent_headers is None:
            parent_headers = self.get_parent_headers()
        return Chunk(
            headers=parent_headers,
            content=list(self.iter_content_lines()),
            start_line=self.title.line_idx,
        )

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
