import re
from collections import defaultdict
from typing import TYPE_CHECKING, Literal

import pymupdf  # type: ignore : no stubs

from ....core.components import MarkdownDoc
from ....core.logger import LOGGER
from ....exceptions.exceptions import TextNotFoundException
from ....ml.ocr import (
    DocumentOCREngine,
    OCRBlock,
    OCREngine,
    PageOCREngine,
    TesseractOCR,
)
from .components import TextSpan
from .utils import PdfParserState, render_page

if TYPE_CHECKING:
    from ....ml.orientation_classifiers import OrientationClassifier


class PdfOCR(PdfParserState):
    """This class is intended to be inherited by the PdfParser.
    It groups all functions related to the OCR of the document: detecting the pages
    that need it, turning them upright, running the OCR engine, and post-processing
    the markdown returned by a DocumentOCREngine.
    """

    # Fraction of a page that raster images must cover for it to look scanned
    _SCANNED_PAGE_IMAGE_COVERAGE: float = 0.8
    # Characters a scanned page may carry outside of its margins before it is
    # considered to hold real text
    _SCANNED_PAGE_MAX_CHARS: int = 50
    # Top/bottom band of a page where scanner stamps land, as a fraction of its height
    _PAGE_MARGIN_RATIO: float = 0.08
    # Markdown header line, as returned by the document OCR engines
    _RE_MD_HEADER: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.*)$")
    # Highest header level given to the headers found by OCR, h1 being kept for the main title
    _OCR_TOP_HEADER_LEVEL: int = 2
    # Resolution (dpi) of the page images given to the orientation classifier
    _ORIENTATION_RESOLUTION: int = 72
    # Pages rendered at once for the orientation classifier
    _ORIENTATION_BATCH_SIZE: int = 32
    # Whether each page of the documents holds a single image, sent as such to the DocumentOCREngine
    _PAGES_ARE_IMAGES: bool = False

    use_ocr: Literal["always", "auto", "never"] = "auto"
    ocr_engine: OCREngine
    # Loaded when detect_orientation=True
    orientation_classifier: "OrientationClassifier | None" = None

    @property
    def ocr_language(self) -> str | None:
        """DEPRECATED : the languages used by the Tesseract OCR engine, if used."""
        return (
            self.ocr_engine.language
            if isinstance(self.ocr_engine, TesseractOCR)
            else None
        )

    def check_ocr_config_is_valid(self) -> None:
        """Check that the OCR configuration is valid."""
        self.ocr_engine.validate()

    def _load_orientation_classifier(self) -> None:
        """Loads the orientation classifier using the global backend preference.
        Raises ImportError immediately if the required inference backend is not installed.
        """
        # pylint: disable=import-outside-toplevel
        from ....ml.orientation_classifiers import load_orientation_classifier

        self.orientation_classifier = load_orientation_classifier()

    def _export_ocr_results(self, md_doc: MarkdownDoc) -> None:
        """Adds the OCR metadata and the images found by OCR to the markdown doc.

        Args:
            md_doc (MarkdownDoc): the markdown doc of the parsed document. Modified in place.
        """
        if self.parsed_using_ocr:
            md_doc.metadata["ocr"] = {
                "engine": self.ocr_engine.name,
                "model": self.ocr_engine.model,
                "pages": self.ocr_pages,
            }
            if self.orientation_classifier is not None:
                md_doc.metadata["ocr"]["rotations"] = self.ocr_rotations
        md_doc.images = {
            image.id: image.to_doc_image() for image in self.ocr_images.values()
        }

    def _get_ocr_textpage(self, page: pymupdf.Page) -> pymupdf.TextPage:
        """Runs the PageOCREngine on a page, after turning it upright.

        Args:
            page (pymupdf.Page): the page to OCR.

        Returns:
            pymupdf.TextPage: the textpage holding the text found on the page.
        """
        assert isinstance(self.ocr_engine, PageOCREngine)
        self.turn_pages_upright([page])
        self.ocr_pages.append(page.number)  # type: ignore : missing typing in pymupdf -> page.number: int

        return self.ocr_engine.get_textpage(page)

    def _parse_document_with_ocr(self) -> None:
        """Parses the document with the DocumentOCREngine. The document then
        bypasses the span-based pipeline: only self.ocr_blocks and self.ocr_images are set.
        """
        assert isinstance(self.ocr_engine, DocumentOCREngine)
        self.spans = []
        self.turn_pages_upright(
            list(self.document.pages(start=self.page_start, stop=self.page_end))  # type: ignore : missing typing in pymupdf -> document.pages() : generator[Page]
        )
        ocr_document = self.ocr_engine.ocr_document(
            self.document,
            self.page_start,
            self.page_end,  # type: ignore : page_end is set by _set_page_range()
            pages_are_images=self._PAGES_ARE_IMAGES,
        )
        if not any(
            block.text.strip()
            for block in ocr_document.blocks
            if not block.is_header_footer
        ):
            raise TextNotFoundException(
                "No text content found in document, even though OCR was used."
            )
        self.ocr_pages = ocr_document.pages
        self.ocr_images = ocr_document.images
        self.main_title = PdfOCR._pop_ocr_main_title(ocr_document.blocks)
        self.ocr_blocks = PdfOCR._normalize_ocr_headers(ocr_document.blocks)

    @staticmethod
    def _pop_ocr_main_title(blocks: list[OCRBlock]) -> str:
        """Finds the main title among the blocks found by OCR and removes its block.
        The main title is the first title of the first page holding content.

        Args:
            blocks (list[OCRBlock]): the blocks found by OCR. Modified in place.

        Returns:
            str: the main title, or an empty string if none was found.
        """
        content_blocks = [block for block in blocks if not block.is_header_footer]
        if not content_blocks:
            return ""
        first_page = content_blocks[0].page
        title_block = next(
            (
                block
                for block in content_blocks
                if block.page == first_page and block.type == "title"
            ),
            None,
        )
        if title_block is None:
            return ""
        blocks.remove(title_block)
        main_title = " ".join(
            line.strip().lstrip("#").strip()
            for line in title_block.text.splitlines()
            if line.strip()
        )

        return main_title[:100] + "[...]" if len(main_title) > 100 else main_title

    @staticmethod
    def _normalize_ocr_headers(blocks: list[OCRBlock]) -> list[OCRBlock]:
        """Shifts the levels of the headers found by OCR so that the highest one is h2,
        h1 being kept for the main title. OCR engines tend to return arbitrary levels,
        such as h1 for all headers or h3 for the highest one.

        Args:
            blocks (list[OCRBlock]): the blocks found by OCR.

        Returns:
            list[OCRBlock]: the blocks, with headers modified in place.
        """
        levels = [
            len(match.group(1))
            for block in blocks
            for line in block.text.splitlines()
            if (match := PdfOCR._RE_MD_HEADER.match(line))
        ]
        if not levels:
            return blocks
        shift = PdfOCR._OCR_TOP_HEADER_LEVEL - min(levels)

        def shift_header(match: re.Match[str]) -> str:
            level = min(max(len(match.group(1)) + shift, 1), 6)
            return f"{"#" * level} {match.group(2)}"

        for block in blocks:
            block.text = "\n".join(
                PdfOCR._RE_MD_HEADER.sub(shift_header, line)
                for line in block.text.splitlines()
            )

        return blocks

    def _get_scanned_pages(self) -> list[int]:
        """Gets the parsed pages that are scanned images holding no real text.

        Scanners routinely stamp a date, a time or a page number onto the image
        they produce, so such pages do yield a few spans and cannot be spotted
        by span count alone. Text volume alone is not enough either: a filled-in
        form or a section divider page legitimately carries a single line. What
        separates them is that a scan is a page-sized raster image while a digital
        page is not.

        Returns:
            list[int]: the numbers of the pages that are image-covered and nearly
                textless, meaning their content is only reachable through OCR.
        """
        spans_per_page: defaultdict[int, list[TextSpan]] = defaultdict(list)
        for span in self.spans:
            spans_per_page[span.page].append(span)

        return [
            page.number  # type: ignore : missing typing in pymupdf -> page.number : int
            for page in self.document.pages(start=self.page_start, stop=self.page_end)  # type: ignore : missing typing in pymupdf -> document.pages() : generator[Page]
            # Cheap check first: a page with real text is ruled out
            # without ever inspecting its images.
            if PdfOCR._count_body_chars(spans_per_page[page.number], page.rect)  # type: ignore : missing typing in pymupdf -> page.number : int, page.rect : Rect
            <= self._SCANNED_PAGE_MAX_CHARS
            and PdfOCR._get_page_image_coverage(page)
            >= self._SCANNED_PAGE_IMAGE_COVERAGE
        ]

    def _warn_scanned_pages_without_ocr(self, scanned_pages: list[int]) -> None:
        """Warns about the pages of a partially scanned document that did not
        go through OCR, as their content is missing from the parsed document.

        Args:
            scanned_pages (list[int]): the pages that are scanned images holding no real text.
        """
        missed_pages = [page for page in scanned_pages if page not in self.ocr_pages]
        if missed_pages:
            LOGGER.warning(
                'Document seems partially scanned: %i page(s) holding no text did not go through OCR, their content is missing: %s. Set use_ocr="always" to run the OCR on the whole document.',
                len(missed_pages),
                missed_pages,
            )

    @staticmethod
    def _count_body_chars(spans: list[TextSpan], page_rect: pymupdf.Rect) -> int:
        """Counts the characters a page holds, ignoring stamps.

        A stamp burnt into a margin by a scanner or a printer (a date, a time, a
        page number) is not text the document actually carries. Counting it would
        hide the fact that the page's real content is only reachable through OCR,
        so spans lying entirely in the top or bottom margin band are discarded,
        as are spans already flagged as repeated headers/footers.

        Args:
            spans (list[TextSpan]): the spans found on the page.
            page_rect (pymupdf.Rect): the rectangle of the page.

        Returns:
            int: the number of characters outside of the page margins.
        """
        margin = page_rect.height * PdfOCR._PAGE_MARGIN_RATIO  # type: ignore : missing typing in pymupdf -> Rect.height : float
        top_limit: float = page_rect.y0 + margin  # type: ignore : missing typing in pymupdf -> Rect.y0 : float
        bottom_limit: float = page_rect.y1 - margin  # type: ignore : missing typing in pymupdf -> Rect.y1 : float

        return sum(
            len(span.text.strip())
            for span in spans
            if not span.is_header_footer
            and span.bbox.y1 > top_limit  # type: ignore : missing typing in pymupdf -> Rect.y1 : float
            and span.bbox.y0 < bottom_limit  # type: ignore : missing typing in pymupdf -> Rect.y0 : float
        )

    @staticmethod
    def _get_page_image_coverage(page: pymupdf.Page) -> float:
        """Computes the fraction of a page covered by raster images.

        Overlapping images are counted once per image rather than once per
        covered area, so the result is capped at 1.0. Overestimating is harmless
        here: the value is only compared against a coverage threshold, and the
        text check has already ruled out pages that carry content.

        Args:
            page (pymupdf.Page): the page to measure.

        Returns:
            float: the covered fraction, between 0.0 and 1.0.
        """
        page_rect: pymupdf.Rect = page.rect  # type: ignore : missing typing in pymupdf -> page.rect : Rect
        page_area: float = page_rect.get_area()  # type: ignore : missing typing in pymupdf -> Rect.get_area() : float
        if not page_area:
            return 0.0

        covered_area = 0.0
        for image_info in page.get_image_info():  # type: ignore : missing typing in pymupdf -> page.get_image_info() : list[dict]
            # Clip to the page: images can bleed outside of it.
            image_rect = pymupdf.Rect(image_info["bbox"]) & page_rect
            if not image_rect.is_empty:  # type: ignore : missing typing in pymupdf -> Rect.is_empty : bool
                covered_area += image_rect.get_area()  # type: ignore : missing typing in pymupdf -> Rect.get_area() : float

        return min(covered_area / page_area, 1.0)

    def turn_pages_upright(self, pages: list[pymupdf.Page]) -> None:
        """Rotates the pages that the orientation classifier confidently finds
        rotated, so that the OCR engine gets them upright.
        Does nothing if no orientation classifier is set.

        Args:
            pages (list[pymupdf.Page]): the pages to turn upright. Modified in place.
        """
        if self.orientation_classifier is None:
            return
        for batch_start in range(0, len(pages), self._ORIENTATION_BATCH_SIZE):
            batch = pages[batch_start : batch_start + self._ORIENTATION_BATCH_SIZE]
            images = [render_page(page, self._ORIENTATION_RESOLUTION) for page in batch]
            predictions = self.orientation_classifier.predict(images)
            for page, prediction in zip(batch, predictions):  # type: ignore : predict() returns a list when given a list
                if prediction.angle == 0 or not prediction.is_confident:
                    continue
                page.set_rotation((page.rotation - prediction.angle) % 360)  # type: ignore : missing typing in pymupdf
                self.ocr_rotations[page.number] = prediction.angle  # type: ignore : missing typing in pymupdf -> page.number: int
                LOGGER.info(
                    "Page %i found rotated by %i°, turned upright before OCR (confidence: %.2f).",
                    page.number,  # type: ignore : missing typing in pymupdf -> page.number: int
                    prediction.angle,
                    prediction.confidence,
                )
