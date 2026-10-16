import warnings
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path
from typing import Any, Literal

import pymupdf  # type: ignore : no stubs

from ...core.components import MarkdownDoc
from ...core.logger import LOGGER
from ...decorators.decorators import mem_debug, timeit, validate_args
from ...exceptions.exceptions import (
    PageNotFoundException,
    PdfParserException,
    TextNotFoundException,
)
from ...ml.ocr import DocumentOCREngine, OCREngine, PageOCREngine, TesseractOCR
from .tools import (
    DocSpecsExtraction,
    PdfExport,
    PdfLinkExtraction,
    PdfOCR,
    PdfPageClassification,
    PdfParserState,
    PdfPlotter,
    PdfTableExtraction,
    PdfTocExtraction,
    TableFinder,
    TextBlock,
    TextLine,
    TextSpan,
)


class PdfParser(
    PdfPageClassification,
    PdfLinkExtraction,
    PdfTableExtraction,
    PdfTocExtraction,
    PdfOCR,
    PdfPlotter,
    PdfExport,
    DocSpecsExtraction,
    PdfParserState,
):
    """Class that parses the document."""

    # Tolerance (pts) for grouping spans on the same y-position into one line
    _LINE_Y_TOLERANCE: int = 3
    # Extra gap (pts) added on top of body_line_spacing to detect block boundaries
    _BLOCK_SPACING_TOLERANCE: int = 2

    table_finder: TableFinder
    extract_tables: bool = True
    add_headers: bool = True
    body_line_spacing: float | None = None

    def __init__(
        self,
        *,
        extract_tables: bool = True,
        table_finder: TableFinder = TableFinder(),
        add_headers: bool = True,
        use_ocr: Literal["always", "auto", "never"] = "auto",
        ocr_engine: OCREngine | None = None,
        ocr_language: str | None = None,
        body_line_spacing: float | None = None,
        detect_orientation: bool = False,
        detect_pages_to_embed: bool = False,
        enable_ml_features: bool | None = None,
    ) -> None:
        """Initializes a PDF parser.

        Args:
            extract_tables (bool, optional): whether or not tables should be extracted.
                Defaults to True.
            add_headers (bool, optional): if True, the parser will try to find a table of content.
                either in documents or in metadata and style the headers accordingly.
                Defaults to True.
            use_ocr (str, optional): whether or not OCR should be used.
                Allows to detect text on images but keep in mind that
                this might include text you actually do not want, such as screenshots.
                Must be one of ["always", "auto", "never"]. Default to "auto".
                With a PageOCREngine (such as TesseractOCR), "auto" runs the OCR on the pages that have no text.
                With a DocumentOCREngine (such as MistralOCR), "auto" runs the OCR on the whole document
                if no text is found in it.
            ocr_engine (OCREngine | None, optional): the OCR engine to use, such as
                TesseractOCR(language="fra+eng") or MistralOCR(image_captioning=True).
                If None, defaults to TesseractOCR().
            ocr_language (str, optional) : DEPRECATED, use ocr_engine=TesseractOCR(language=...) instead.
                The languages to consider for OCR with the default Tesseract engine.
                Must be a string of 3 letter codes languages separated by "+".
                Example : "fra+eng+ita"
            body_line_spacing (float, optional) : the size of the space between 2 lines of the body
                of the document. Generally around 1. If None, an automatic method will try to find it.
                Tweak this parameter for better merging of lines into blocks.
            table_finder (TableFinder | None, optional): the table finder to use for parsing the tables.
                If None, defauts to a TableFinder with default parameters.
            detect_orientation (bool, optional): if True, the pages going through OCR are turned
                upright beforehand, according to an ML orientation classifier loaded on startup.
                Requires ``onnxruntime`` or ``openvino`` and ``huggingface-hub``.
                Use :func:`chunknorris.ml.set_ml_backend` to select the inference backend.
                Defaults to False.
            detect_pages_to_embed (bool, optional): if True, loads the ML page classifier on startup
                so that :meth:`classify_pages` and :meth:`get_images_of_pages_to_embed` are available.
                Requires ``onnxruntime`` or ``openvino`` and ``huggingface-hub``.
                Use :func:`chunknorris.ml.set_ml_backend` to select the inference backend.
                Defaults to False.
            enable_ml_features (bool, optional): DEPRECATED, use detect_pages_to_embed instead.
        """
        super().__init__()
        self.add_headers = add_headers
        self.extract_tables = extract_tables
        self.use_ocr = use_ocr
        if ocr_language is not None:
            if ocr_engine is not None:
                raise ValueError(
                    "ocr_language can't be used along with ocr_engine. Use ocr_engine=TesseractOCR(language=...) instead."
                )
            warnings.warn(
                "ocr_language is deprecated and will be removed in a future version. Use ocr_engine=TesseractOCR(language=...) instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.ocr_engine = ocr_engine or TesseractOCR(language=ocr_language or "fra+eng")
        self.body_line_spacing = body_line_spacing
        self._configured_body_line_spacing = (
            body_line_spacing  # preserved for cleanup reset
        )
        self.table_finder = table_finder
        if enable_ml_features is not None:
            warnings.warn(
                "enable_ml_features is deprecated and will be removed in a future version. Use detect_pages_to_embed instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            detect_pages_to_embed = detect_pages_to_embed or enable_ml_features
        if detect_pages_to_embed:
            self._load_page_classifier()
        if detect_orientation and use_ocr == "never":
            warnings.warn(
                'detect_orientation is ignored with use_ocr="never": orientation is only detected on the pages going through OCR.',
                UserWarning,
                stacklevel=2,
            )
        elif detect_orientation:
            self._load_orientation_classifier()

        if self.use_ocr != "never":
            self.check_ocr_config_is_valid()

    @timeit
    @validate_args
    def parse_file(
        self,
        filepath: str,
        page_start: int = 0,
        page_end: int | None = None,
    ) -> MarkdownDoc:
        """Parses a pdf document and returns
        the parsed MarkdownDoc object.

        Args:
            filepath (str): the path to the file to parse.
            page_start (int, optional): the page to start parsing from. Defaults to 0.
            page_end (int, optional): the page to stop parsing. None to parse until last page. Defaults to None.

        Returns:
            MarkdownDoc: The MarkdownDoc to be passed to MarkdownChunker.
        """
        self.read_file(filepath)
        return self._parse_and_export(page_start, page_end)

    @timeit
    @validate_args
    def parse_string(
        self, string: bytes, page_start: int = 0, page_end: int | None = None
    ) -> MarkdownDoc:
        """Parses a byte string obtained from a pdf document
        and returns its corresponding Markdown formatted string.

        Args:
            string (bytes): a bytes stream.
            page_start (int, optional): the page to start parsing from. Defaults to 0.
            page_end (int, optional): the page to stop parsing. None to parse until last page. Defaults to None.

        Returns:
            MarkdownDoc: The MarkdownDoc to be passed to MarkdownChunker.
        """
        self.read_file(string)
        return self._parse_and_export(page_start, page_end)

    @mem_debug("read_file")
    def read_file(self, filepath_or_stream: str | bytes) -> None:
        """Wrapper of pymupdf.open() that simply read the file content.
        Isolates the file opening to set self.document without running the parsing
        so that methods that don't need the parsing but need self.document can be run.

        Args:
            filepath_or_stream (str | bytes): Filepath to a pdf file, or byte stream.
        """
        self.cleanup_memory()

        if isinstance(filepath_or_stream, str):
            self.filepath = filepath_or_stream
            if Path(filepath_or_stream).suffix.lower() != ".pdf":
                raise PdfParserException("Only .pdf files can be passed to PdfParser.")
            self.document = pymupdf.open(filepath_or_stream, filetype="pdf")
        else:
            self.document = pymupdf.open(stream=filepath_or_stream, filetype="pdf")

    def _parse_and_export(self, page_start: int, page_end: int | None) -> MarkdownDoc:
        """Shared implementation for parse_file and parse_string.
        The document is kept open after parsing so that plotting methods
        (plot_pdf, plot_drawings, etc.) remain usable. Call cleanup_memory()
        or parse a new file to release it.
        """
        try:
            self._set_page_range(page_start, page_end)
            self._parse_document()
            md_doc = self.to_markdown_doc()
            self._export_ocr_results(md_doc)
            return md_doc
        except Exception:
            if isinstance(self._document, pymupdf.Document):
                self._document.close()
            self._document = None
            raise

    def _set_page_range(self, page_start: int, page_end: int | None) -> None:
        """Initializes the self.page_start and self.page_end

        Args:
            page_start (int): the page to start parsing from. Defaults to 0.
            page_end (int | None): the page to stop parsing.
        """
        self.page_start = page_start
        if self.document.page_count == 0:  # type: ignore : missing typing in pymupdf -> document.page_count : int
            raise PageNotFoundException("The provided document contains no pages !")
        if page_end is None:
            self.page_end = self.document.page_count  # type: ignore : missing typing in pymupdf -> document.page_count : int
        else:
            self.page_end = min(page_end, self.document.page_count)  # type: ignore : missing typing in pymupdf -> document.page_count : int
        if self.page_start >= self.page_end:  # type: ignore : missing typing in pymupdf -> document.page_count : int
            raise ValueError("Arg 'page_end' must be greater than 'page_start'.")

    def _parse_document(self) -> None:
        """Parses a pdf document."""
        uses_document_ocr = isinstance(self.ocr_engine, DocumentOCREngine)
        if uses_document_ocr and self.use_ocr == "always":
            LOGGER.info(
                'Running OCR on the document with %r (use_ocr="always").',
                self.ocr_engine,
            )
            self._parse_document_with_ocr()
            return

        self.spans = self._create_spans()
        scanned_pages = self._get_scanned_pages() if self.spans else []
        # The decision is deliberately taken for the document as a whole. A single
        # page bearing only a section title must not make the parser give up on the
        # pages around it that do hold text.
        if (
            not self.spans
            or all(span.is_header_footer for span in self.spans)
            or len(scanned_pages) == self.page_end - self.page_start  # type: ignore : page_end is set by _set_page_range()
        ):
            if uses_document_ocr and self.use_ocr == "auto":
                LOGGER.info(
                    "No text found in document. Running OCR on the document with %r.",
                    self.ocr_engine,
                )
                self._parse_document_with_ocr()
                return
            raise TextNotFoundException(
                "No text content found in document, even though OCR was used."
                if self.use_ocr == "always"
                else 'No text content found in document. You may want to set use_ocr="always".'
            )
        self._warn_scanned_pages_without_ocr(scanned_pages)
        self.tables = self.get_tables() if self.extract_tables else []
        self.spans = self._flag_table_spans(self.spans)
        self.lines = PdfParser._create_lines(self.spans)
        self.blocks = self._create_blocks(self.lines)
        self._set_document_specifications()
        self._flag_footnotes(self.spans)
        self.main_title = self._get_document_main_title()
        self.toc = self.get_toc() if self.add_headers else []

    @mem_debug("_create_spans")
    def _create_spans(self) -> list[TextSpan]:
        """Prepares the parsed spans.

        Returns:
            list[textSpan]: the spans, after preprocessing.
        """
        spans = self._extract_spans()
        for i, span in enumerate(spans):
            span.order = i
        spans = self._flag_headers_footers(spans)
        spans = self._bind_links_to_spans(spans)

        return spans

    def _extract_spans(self) -> list[TextSpan]:
        """Get the spans of the pages."""

        spans: list[TextSpan] = []
        # Document OCR engines run on the whole document, not page per page
        use_ocr = (
            self.use_ocr if isinstance(self.ocr_engine, PageOCREngine) else "never"
        )
        for page in self.document.pages(start=self.page_start, stop=self.page_end):  # type: ignore : missing typing in pymupdf -> document.pages() : generator[Page]
            match use_ocr:
                case "always":
                    textpage = self._get_ocr_textpage(page)
                case "auto":
                    textpage: pymupdf.TextPage = page.get_textpage()  # type: ignore : missing typing in pymupdf
                    page_spans = PdfParser._extract_spans_from_textpage(
                        textpage, page.number  # type: ignore : missing typing in pymupdf -> page.number: int
                    )
                    if page_spans:
                        spans.extend(page_spans)
                        continue
                    textpage = self._get_ocr_textpage(page)
                case "never":
                    textpage: pymupdf.TextPage = page.get_textpage()  # type: ignore : missing typing in pymupdf
            spans.extend(PdfParser._extract_spans_from_textpage(textpage, page.number))  # type: ignore : missing typing in pymupdf -> page.number: int
        if self.ocr_pages:
            LOGGER.info(
                "OCR used with %r on %i page(s): %s",
                self.ocr_engine,
                len(self.ocr_pages),
                self.ocr_pages,
            )

        return spans

    @staticmethod
    def _extract_spans_from_textpage(
        textpage: pymupdf.TextPage, page_number: int
    ) -> list[TextSpan]:
        """Extracts a list of spans from a TextPage.

        Args:
            textpage (pymupdf.TextPage): the TextPage to extract the spans from.
            page_number (int): the page number of the provided textpage.

        Returns:
            list[TextSpan]: a list of textspan objects
        """
        page_dict: dict[str, Any] = textpage.extractDICT()  # type: ignore : missing typing in pymupdf

        return [
            TextSpan(page=page_number, orientation=line["dir"], **span)
            for block in page_dict["blocks"]
            for line in block["lines"]
            for span in line["spans"]
        ]

    def _flag_table_spans(self, spans: list[TextSpan]) -> list[TextSpan]:
        """Flags the span if it belongs to any table
        already parsed in the tables.
        Stores the value in span.isin_table attribute.

        Args:
            spans (list[TextSpan]) : the list of spans.

        Returns:
            list[TextSpan] : the list of spans with added attribute "isin_table".
        """
        page_tables: defaultdict[int, list[pymupdf.Rect]] = defaultdict(list)
        for table in self.tables:
            page_tables[table.page].append(table.bbox)

        for span in spans:
            span.isin_table = any(
                rect.contains(span.origin) for rect in page_tables[span.page]  # type: ignore : missing typing in pymupdf | Rect.contains(x) : bool
            )

        return spans

    def _flag_headers_footers(self, spans: list[TextSpan]) -> list[TextSpan]:
        """Flags spans that are headers and footers (inplace).
        A span is considered a header/footer if its exact bbox appears on more
        than 33% of the pages of the document.

        Args:
            spans (list[TextSpan]): the list of spans with attribute is_header_footer updated.
        """
        if self.document.page_count <= 2:  # type: ignore : missing typing in pymupdf | document.page_count : int
            return spans

        bbox_location_counts: Counter[pymupdf.Rect] = Counter(
            span.bbox for span in spans
        )
        header_footer_bboxes = {
            bbox
            for bbox, count in bbox_location_counts.items()
            if count > self.document.page_count / 3  # type: ignore : missing typing in pymupdf | document.page_count : int
        }
        for span in spans:
            span.is_header_footer = span.bbox in header_footer_bboxes

        return spans

    def _flag_footnotes(self, spans: list[TextSpan]) -> None:
        """Flags spans that belong to footnotes (inplace).
        A span is considered a footnote if its font size is smaller than the
        minimum body font size and it sits in the bottom 20 % of its page.
        Footnote spans are NOT excluded from the output; they are rendered as
        blockquotes in the final markdown to visually separate them.

        Must be called after _set_document_specifications so that
        self.main_body_fontsizes is available.

        Args:
            spans (list[TextSpan]): the list of spans to annotate.
        """
        if not self.main_body_fontsizes:
            return
        min_body_fontsize = min(self.main_body_fontsizes)

        # Pre-compute page heights once to avoid repeated document access
        page_heights: dict[int, float] = {
            page.number: page.rect.height  # type: ignore : missing typing in pymupdf | Page.number : int, Rect.height : float
            for page in self.document.pages(start=self.page_start, stop=self.page_end)  # type: ignore : missing typing in pymupdf
        }

        for span in spans:
            if span.is_header_footer or span.isin_table or span.is_superscripted:
                continue
            page_height = page_heights.get(span.page, float("inf"))
            span.is_footnote = (
                span.fontsize < min_body_fontsize
                and span.bbox.y0 > page_height * 0.8  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            )

    @staticmethod
    @mem_debug("_create_lines")
    def _create_lines(spans: list[TextSpan]) -> list[TextLine]:
        """Consolidate the consecutive spans by grouping them together
        in a TextLine when possible if they belong to the same line.
        Spans can be merged if:
        - they do not belong to table or header/footer
        - they have the same y positions
        Non-dominant orientations per page are filtered out to remove rotated
        watermarks or margin labels (e.g. "CONFIDENTIAL", arXiv IDs).
        Args:
            spans (list[TextSpan]): the list of spans.

        Returns:
            list[TextLine]: the list of lines.
        """
        if len(spans) == 0:
            return []

        lines: list[TextLine] = []
        # do not consider footer/header or table spans
        spans_to_merge = [
            span for span in spans if not span.is_header_footer and not span.isin_table
        ]

        # Determine dominant text orientation per page.
        # Pages where one orientation dominates keep only that orientation,
        # which removes rotated watermarks and margin stamps without discarding
        # legitimately rotated pages (e.g. landscape scans).
        page_orientation_counts: defaultdict[int, Counter[tuple[float, float]]] = (
            defaultdict(Counter)
        )
        for span in spans_to_merge:
            page_orientation_counts[span.page][span.orientation] += 1
        page_dominant_orientation: dict[int, tuple[float, float]] = {
            page: counts.most_common(1)[0][0]
            for page, counts in page_orientation_counts.items()
        }
        spans_to_merge = [
            span
            for span in spans_to_merge
            if span.orientation == page_dominant_orientation.get(span.page, (1.0, 0.0))
        ]

        # Group spans by page. _extract_spans yields spans in page order, so groupby
        # produces exactly one group per page without needing a sort.
        spans_grouped_per_page = (
            list(spans_on_page)
            for _, spans_on_page in groupby(spans_to_merge, key=lambda span: span.page)
        )
        for spans_on_page in spans_grouped_per_page:
            buffer = [spans_on_page[0]]
            for span in spans_on_page[1:]:
                # Adaptive tolerance: larger fonts tolerate a bigger y-offset between
                # spans on the same visual line (e.g. mixed font sizes in headings).
                y_tolerance = max(
                    PdfParser._LINE_Y_TOLERANCE,
                    0.25 * buffer[-1].line_height,
                )
                if abs(span.origin.y - buffer[-1].origin.y) <= y_tolerance or span.is_superscripted:  # type: ignore : missing typing in pymupdf | Point.y : float
                    buffer.append(span)
                else:
                    lines.append(TextLine(buffer))
                    buffer = [span]
            lines.append(TextLine(buffer))

        return lines

    @staticmethod
    def _get_line_spacing(lines: list[TextLine]) -> float:
        """Determine the linespace of the body of the document's content.
        It this case, "linespace" refers to the vertical distance
        between the bboxes of 2 consecutive lines.
        This linespace can be used to merge the lines together into blocks.

        Args:
            lines (list[TextLine]): the parsed lines.

        Returns:
            float: the value of the linespace. 0.0 when it cannot be estimated,
                i.e. when the document holds fewer than two comparable lines
                (single-line forms, mostly-scanned pages). Blocks are then split
                on any gap wider than _BLOCK_SPACING_TOLERANCE.
        """
        # Focus on the most common fontsize so that list items, titles, or footnotes
        # with different fontsizes do not skew the body linespacing estimate.
        fontsize_counts = Counter(line.fontsize for line in lines if not line.is_empty)
        body_fontsize = (
            fontsize_counts.most_common(1)[0][0] if fontsize_counts else None
        )

        linespace_counts = Counter(
            round(curr_line.bbox.y0 - prev_line.bbox.y1, 1)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            for curr_line, prev_line in zip(lines[1:], lines[:-1])
            # Negative spacings occur between columns in multi-column layouts; skip them
            # as they would corrupt the linespace estimate used for block merging.
            if curr_line.bbox.y0 >= prev_line.bbox.y0  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            and (
                body_fontsize is None
                or (
                    prev_line.fontsize == body_fontsize
                    and curr_line.fontsize == body_fontsize
                )
            )
        )

        if not linespace_counts:
            # Fallback: use all lines if no body-fontsize pairs were found
            linespace_counts = Counter(
                round(curr_line.bbox.y0 - prev_line.bbox.y1, 1)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                for curr_line, prev_line in zip(lines[1:], lines[:-1])
                if curr_line.bbox.y0 >= prev_line.bbox.y0  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            )

        if not linespace_counts:
            return 0.0

        return max(linespace_counts, key=linespace_counts.get)

    @mem_debug("_create_blocks")
    def _create_blocks(self, lines: list[TextLine]) -> list[TextBlock]:
        """Groups lines together into blocks.
        A block is a group of lines the is not separated by extra spacing.
        For example, it can be a paragraph, or the title of a section.

        Args:
            lines (list[TextLine]): the lines to group.
            body_linespacing (float): the distance between the bboxes of two.
                consecutive lines below which 2 lines are considered belonging to the same block.

        Returns:
            list[TextBlock]: the blocks.
        """
        if len(lines) == 0:
            return []
        if self.body_line_spacing is None:
            self.body_line_spacing = PdfParser._get_line_spacing(lines)

        blocks: list[TextBlock] = []
        buffer = [lines[0]]
        for line in lines[1:]:
            # if previous line was emtpy ("\n") => new block
            # or if lines have different fontsizes => new block
            # or if new line is far up above previous line, might be new column in multicolumn document => new block
            # or if new line "far away" from previous line => new block
            if (
                buffer[-1].is_empty
                or line.fontsize != buffer[-1].fontsize
                or line.bbox.y0 - self.body_line_spacing - self._BLOCK_SPACING_TOLERANCE > buffer[-1].bbox.y1  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                or line.bbox.y1 <= buffer[-1].bbox.y0  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            ):  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                blocks.append(TextBlock(buffer))
                buffer = [line]
            # Two consecutive lines belong to the same block
            else:
                buffer.append(line)
        blocks.append(TextBlock(buffer))

        return blocks

    @mem_debug("cleanup_memory")
    def cleanup_memory(self) -> None:
        """Cleans up memory by reseting all objects created to parse the document."""
        if isinstance(self._document, pymupdf.Document):
            self._document.close()
        self._document = None
        self.filepath = None
        self.page_start = 0
        self.page_end = None
        self.spans = []
        self.lines = []
        self.blocks = []
        self.tables = []
        self.ocr_blocks = []
        self.ocr_images = {}
        self.ocr_pages = []
        self.ocr_rotations = {}
        self.toc = []
        self.main_title = ""
        self.document_fontsizes = []
        self.main_body_fontsizes = []
        self.main_body_is_bold = False
        # restore the user-configured value; auto-detected value is no longer valid
        self.body_line_spacing = self._configured_body_line_spacing
        # release cached page images — the PIL objects can be large
        self._page_images = None
        self._page_images_resolution = 100
