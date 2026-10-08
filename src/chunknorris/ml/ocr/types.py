"""Data structures returned by the OCR engines."""

from __future__ import annotations

from dataclasses import dataclass, field

import pymupdf  # type: ignore : no stubs

# Block types that must not end up in the exported markdown
HEADER_FOOTER_BLOCK_TYPES = frozenset({"header", "footer"})


@dataclass
class OCRImage:
    """An image found by a document OCR engine.

    Attributes:
        id: identifier of the image, used as link target in the markdown.
        page: the page the image belongs to (0-based).
        bbox: the location of the image on the page, in PDF points.
        image_type: the category of the image (chart, screenshot, signature...),
            if the engine annotated it.
        caption: a textual description of the image, if the engine annotated it.
        base64: the base64 encoded image (data URI), if the engine returned it.
    """

    id: str
    page: int
    bbox: pymupdf.Rect
    image_type: str | None = None
    caption: str | None = None
    base64: str | None = None


@dataclass
class OCRBlock:
    """A block of content found by a document OCR engine, such as a title,
    a paragraph, a table or an image. Exposes the same interface
    as TextBlock and PdfTable so that it can be exported by PdfExport
    and plotted by PdfPlotter.

    Attributes:
        type: the type of block (title, text, list, table, image, signature, header, footer...).
        text: the markdown content of the block.
        bbox: the location of the block on the page, in PDF points.
        page: the page the block belongs to (0-based).
        order: the position of the block in the reading order of the document.
        image_id: the id of the related OCRImage, if the block is an image.
    """

    type: str
    text: str
    bbox: pymupdf.Rect
    page: int
    order: int = 0
    image_id: str | None = None

    @property
    def is_header_footer(self) -> bool:
        return self.type in HEADER_FOOTER_BLOCK_TYPES

    def to_markdown(self) -> str:
        return self.text


@dataclass
class OCRDocument:
    """The result of the OCR of a document.

    Attributes:
        engine: the name of the OCR engine used.
        model: the model used by the engine, if any.
        pages: the 0-based numbers of the pages that went through OCR.
        blocks: the blocks of the document, in reading order.
        images: the images of the document, mapped by id.
    """

    engine: str
    model: str | None = None
    pages: list[int] = field(default_factory=list)
    blocks: list[OCRBlock] = field(default_factory=list)
    images: dict[str, OCRImage] = field(default_factory=dict)
