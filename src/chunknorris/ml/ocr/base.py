from abc import ABC, abstractmethod

import pymupdf  # type: ignore : no stubs

from .types import OCRDocument


class OCREngine(ABC):
    """Base class of all OCR engines.

    Engines come in two flavours:
    - PageOCREngine: runs page per page and returns pymupdf TextPages,
        that go through the regular span-based parsing pipeline.
    - DocumentOCREngine: runs on the whole document and returns markdown blocks,
        that bypass the span-based parsing pipeline.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the engine, stored in the metadata of the parsed documents."""

    @property
    def model(self) -> str | None:
        """Model used by the engine, if any."""
        return None

    @abstractmethod
    def validate(self) -> None:
        """Checks that the engine is properly configured.

        Raises:
            OCRException: if the engine can't be used.
        """


class PageOCREngine(OCREngine):
    """OCR engine running page per page, returning pymupdf TextPages."""

    @abstractmethod
    def get_textpage(self, page: pymupdf.Page) -> pymupdf.TextPage:
        """Runs the OCR on a page.

        Args:
            page (pymupdf.Page): the page to OCR.

        Returns:
            pymupdf.TextPage: the textpage holding the text found on the page.
        """


class DocumentOCREngine(OCREngine):
    """OCR engine running on the whole document, returning markdown blocks."""

    @abstractmethod
    def ocr_document(
        self,
        document: pymupdf.Document,
        page_start: int,
        page_end: int,
        pages_are_images: bool = False,
    ) -> OCRDocument:
        """Runs the OCR on a range of pages of a document.

        Args:
            document (pymupdf.Document): the document to OCR.
            page_start (int): the first page to OCR (included).
            page_end (int): the last page to OCR (excluded).
            pages_are_images (bool, optional): if True, each page holds a single image
                (e.g. the frames of an image converted to a pdf), and the engine may send
                the rendered pages as images rather than as a pdf. Defaults to False.

        Returns:
            OCRDocument: the blocks and images found, with page numbers
                relative to the whole document.
        """
