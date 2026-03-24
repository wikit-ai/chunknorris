import re
from collections import defaultdict
from functools import cached_property
from typing import Literal

import pymupdf  # type: ignore : no stubs
from pydantic import BaseModel, Field

# Matches common numbered-list prefixes: "1. ", "1) ", "a. ", "a) ", "(i) ", "(A) "
_NUMBERED_LIST_RE = re.compile(
    r"^\s*(\d+[.)]\s+|[a-zA-Z][.)]\s+|\([a-zA-Z0-9ivxlIVXL]+\)\s+)"
)

# TODO : Find list of special bullet-list caracters
INVALID_CHAR_MAP = {
    "\xa0": " ",
    "\uf0a7": "",
    "\uf0b7": "- ",
    "–": "- ",
    "•": "- ",
    "●": "- ",
    "►": "- ",
    "": "- ",  # arrow-like bullet
    "": "- ",  # triangle-like bullet
}
# Pre-built translation table for O(1) per-character lookup, single pass over the string
_CHAR_TRANSLATION_TABLE = str.maketrans(INVALID_CHAR_MAP)


class Link:
    def __init__(self, uri: str, bbox: pymupdf.Rect) -> None:
        self.uri = uri
        self.bbox = bbox

    def __str__(self) -> str:
        return self.uri


class TocTitle(BaseModel):
    text: str = Field(description="The title's text.")
    source: Literal["metadata", "regex", "fontsize"] = Field(
        description="The method used to obtain the title."
    )
    page: int = Field(description="The destination page refered by the title.")
    level: int | None = Field(
        default=None,
        description="The title's level. From 1 to 6, such as html headers.",
        gt=0,
    )
    x_offset: float | None = Field(
        default=None,
        description="The horizontal offset from the left of the page of the title's span in the ToC section. Used only if title obtained from 'regex'.",
        gt=0,
    )
    source_page: int | None = Field(
        default=None,
        description="The page where the regex have been matched (supposedly the ToC section). Used only if title obtained from 'regex'.",
    )
    found: bool = Field(
        default=False,
        description="Whether or not the title has been found on the destination page.",
    )


class TextSpan:
    _bbox: pymupdf.Rect
    text: str
    font: str
    fontcolor: int
    raw_fontsize: float
    flags: int
    ascender: float
    descender: float
    origin: pymupdf.Point
    page: int
    # attributes to be modified while processing the pdf
    order: int  # the order of the span among all spans
    isin_table: bool  # whether or not the span is in a table
    is_header_footer: bool  # whether the span is a header or footer
    is_footnote: bool  # whether the span belongs to a footnote
    link: Link | None  # The link bound to this span, if a link is bound

    def __init__(
        self,
        *,
        bbox: tuple[float],
        text: str,
        font: str,
        color: int,
        size: float,
        flags: int,
        ascender: float,
        descender: float,
        origin: tuple[float],
        page: int,
        orientation: tuple[float, float],
        bidi: int | None = None,
        char_flags: int | None = None,
        alpha: int | None = None,
    ) -> None:
        self._bbox = pymupdf.Rect(bbox)
        self.text = TextSpan._remove_invalid_characters(text)
        self.font = font
        self.fontcolor = color
        self.raw_fontsize = size
        self.flags = flags
        self.ascender = ascender
        self.descender = descender
        self.origin = pymupdf.Point(origin)
        self.page = page
        self.orientation = orientation
        self.bidi = bidi
        self.char_flags = char_flags
        self.alpha = alpha

        self.order = 0
        self.isin_table = False
        self.is_header_footer = False
        self.is_footnote = False
        self.link = None

    @property
    def bbox(self) -> pymupdf.Rect:
        return self._bbox

    @property
    def fontsize(self) -> float:
        return round(self.raw_fontsize)

    @property
    def is_superscripted(self) -> bool:
        return bool(self.flags & pymupdf.TEXT_FONT_SUPERSCRIPT)

    @property
    def is_italic(self) -> bool:
        return bool(self.flags & pymupdf.TEXT_FONT_ITALIC)

    @property
    def is_serifed(self) -> bool:
        return bool(self.flags & pymupdf.TEXT_FONT_SERIFED)

    @property
    def is_monospaced(self) -> bool:
        return bool(self.flags & pymupdf.TEXT_FONT_MONOSPACED)

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & pymupdf.TEXT_FONT_BOLD)

    @property
    def line_height(self) -> float:
        return self.bbox.y1 - self.bbox.y0  # type: ignore : missing typing in pymuPdf | Rect.y0 : float, Rect.y1 : float

    @property
    def rgb_fontcolor(self) -> tuple[int, int, int]:
        return pymupdf.sRGB_to_rgb(self.fontcolor)  # type: ignore : missing typing in pymuPdf | pymupdf.sRGB_to_rgb(srgb: int) -> tuple[int, int, int]

    @property
    def is_empty(self) -> bool:
        return not self.text or self.text.isspace()

    @staticmethod
    def _remove_invalid_characters(text: str) -> str:
        """Remove the invalid characters in a string

        Args:
            text (str): the text to cleaup

        Returns:
            str: the cleanedup text
        """
        return text.translate(_CHAR_TRANSLATION_TABLE)

    def to_markdown(self) -> str:
        """Format the span's text to markdown format

        Returns:
            str: the markdown formatted text
        """
        if not self.text:
            return ""
        text = self.text.strip() if not self.link else f"[{self.text}]({self.link.uri})"
        if not self.is_empty:
            if self.is_superscripted:
                text = f"<sup>{text}</sup>"
            if self.is_bold:
                text = f" **{text}** "
            if self.is_italic:
                text = f" *{text}* "

        return text

    def __str__(self) -> str:
        return self.text


class TextLine:
    """A line is a group of spans.

    Most of its attributes values reflect the attributes of most caracters in spans.
    Example : If a TextLine has 2 spans
        - TextSpan(text="blip", line_height=10)
        - TextSpan(text="blipbliblip", line_height=20)
        => then the line height if this textline will be 20, as most caracters have this feature.
    """

    spans: list[TextSpan]
    # attributes to be modified while parsing the document
    is_toc_element: bool

    def __init__(self, spans: list[TextSpan]) -> None:
        self.spans = spans

        self.is_toc_element = False

    @cached_property
    def text(self) -> str:
        return "".join((span.text for span in self.spans)).strip()

    @cached_property
    def bbox(self) -> pymupdf.Rect:
        bbox = self.spans[0].bbox
        for span in self.spans[1:]:
            bbox = bbox.include_rect(span.bbox)  # type: ignore : missing typing in pymuPdf | Rect.include_rect(r: Rect) -> Rect
        return bbox

    @cached_property
    def line_height(self) -> float:
        lineheight_occurences_map: dict[float, int] = defaultdict(int)
        for span in self.spans:
            lineheight_occurences_map[span.line_height] += len(span.text)
        return max(lineheight_occurences_map, key=lineheight_occurences_map.get)

    @cached_property
    def fontsize(self) -> float:
        fontsize_occurences_map: dict[float, int] = defaultdict(int)
        for span in self.spans:
            fontsize_occurences_map[span.fontsize] += len(span.text)
        return max(fontsize_occurences_map, key=fontsize_occurences_map.get)

    @cached_property
    def origin(self) -> pymupdf.Point:
        return pymupdf.Point(
            min((span.origin.x for span in self.spans)),  # type: ignore : missing typing in pymuPdf | Point.x -> float
            max((span.origin.y for span in self.spans)),  # type: ignore : missing typing in pymuPdf | Point.y -> float
        )

    @cached_property
    def page(self) -> int:
        return self.spans[0].page

    @cached_property
    def orientation(self) -> tuple[float, float]:
        return self.spans[0].orientation

    @cached_property
    def is_empty(self) -> bool:
        return all(span.is_empty for span in self.spans)

    @cached_property
    def is_bold(self) -> bool:
        return all(span.is_bold for span in self.spans if not span.is_empty)

    @cached_property
    def is_bullet_point(self) -> bool:
        return self.text.startswith("- ")

    @cached_property
    def is_numbered_list(self) -> bool:
        return bool(_NUMBERED_LIST_RE.match(self.text))

    @property
    def is_header_footer(self) -> bool:
        return all(span.is_header_footer for span in self.spans)

    @property
    def is_footnote(self) -> bool:
        return all(span.is_footnote for span in self.spans if not span.is_empty)

    @property
    def order(self) -> int:
        return min(self.spans, key=lambda x: x.order).order

    def to_markdown(self) -> str:
        """Get the text content of all spans in the line, as markdown

        Returns:
            str: the markdown formatted text
        """
        return " ".join((span.to_markdown() for span in self.spans))

    def __str__(self) -> str:
        return self.text


class TextBlock:
    """A TextBlock is a list of lines"""

    lines: list[TextLine]

    # Attributes to modify while parsing the pdf
    section_title: TocTitle | None  # store the TocTitle if block is a ssection title

    def __init__(self, lines: list[TextLine]) -> None:
        self.lines = lines

        # Attributes to modify while parsing the pdf
        self.section_title = None  # store the TocTitle if block is a ssection title

    @cached_property
    def text(self) -> str:
        return " ".join((line.text for line in self.lines))

    @cached_property
    def bbox(self) -> pymupdf.Rect:
        bbox = self.lines[0].bbox
        for line in self.lines[1:]:
            bbox = bbox.include_rect(line.bbox)  # type: ignore : missing typing in pymuPdf | Rect.include_rect(r: Rect) -> Rect
        return bbox

    @cached_property
    def page(self) -> int:
        return self.lines[0].page

    @cached_property
    def orientation(self) -> tuple[float, float]:
        return self.lines[0].orientation

    @property
    def is_header_footer(self) -> bool:
        return all(line.is_header_footer for line in self.lines)

    @property
    def is_footnote(self) -> bool:
        return all(line.is_footnote for line in self.lines if not line.is_empty)

    @property
    def order(self) -> int:
        return min(self.lines, key=lambda x: x.order).order

    @cached_property
    def is_empty(self) -> bool:
        return all(line.is_empty for line in self.lines)

    @cached_property
    def is_bold(self) -> bool:
        return all(line.is_bold for line in self.lines if not line.is_empty)

    @cached_property
    def fontsize(self) -> float:
        fontsize_occurences_map: dict[float, int] = defaultdict(int)
        for line in self.lines:
            fontsize_occurences_map[line.fontsize] += len(line.text)
        return max(fontsize_occurences_map, key=fontsize_occurences_map.get)

    def to_markdown(self) -> str:
        """Get the text content of all spans in the line, as markdown

        Returns:
            str: the markdown formated text
        """
        if self.is_empty:
            return ""
        md_string = ""
        for i, line in enumerate(self.lines):
            if line.is_bullet_point or line.is_toc_element or line.is_numbered_list:
                md_string += "\n\n" + line.to_markdown().strip() + "\n\n"
            else:
                line_md = line.to_markdown().strip()
                prev_line = self.lines[i - 1] if i > 0 else None
                if (
                    prev_line is not None
                    and not prev_line.is_bullet_point
                    and not prev_line.is_toc_element
                    and prev_line.text.rstrip().endswith("-")
                    and line.text
                    and line.text[0].islower()
                ):
                    # Hyphenated word at line break: strip the hyphen and join directly
                    stripped = md_string.rstrip()
                    if stripped.endswith("-"):
                        md_string = stripped[:-1] + line_md
                    else:
                        md_string += " " + line_md
                else:
                    md_string += " " + line_md
        if self.section_title:
            level = self.section_title.level or 0
            return "\n\n#" + "#" * level + " " + md_string.strip() + "\n\n"
        if self.is_footnote:
            return "> *" + md_string.strip() + "*"
        return md_string.strip()

    def __str__(self) -> str:
        return self.text
