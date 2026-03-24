import os
from collections import Counter, defaultdict
from itertools import groupby

from pathlib import Path
from typing import Any, Literal

import pymupdf  # type: ignore : no stubs

from ...core.components import MarkdownDoc
from ...decorators.decorators import timeit, validate_args
from ...exceptions.exceptions import (
    PageNotFoundException,
    PdfParserException,
    TextNotFoundException,
)
from .tools import (
    DocSpecsExtraction,
    PdfExport,
    PdfLinkExtraction,
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
    PdfLinkExtraction,
    PdfTableExtraction,
    PdfTocExtraction,
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
    use_ocr: Literal["always", "auto", "never"] = "auto"
    ocr_language: str = "fra+eng"
    body_line_spacing: float | None = None

    def __init__(
        self,
        *,
        extract_tables: bool = True,
        table_finder: TableFinder = TableFinder(),
        add_headers: bool = True,
        use_ocr: Literal["always", "auto", "never"] = "auto",
        ocr_language: str = "fra+eng",
        body_line_spacing: float | None = None,
    ) -> None:
        """Initializes a pdf parser.

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
            ocr_language (str, optional) : the languages to consider for OCR.
                Must be a string of 3 letter codes languages separated by "+".
                Example : "fra+eng+ita"
            body_line_spacing (float, optional) : the size of the space between 2 lines of the body
                of the document. Generally around 1. If None, an automatic method will try to find it.
                Tweak this parameter for better merging of lines into blocks.
            table_finder (TableFinder | None, optional): the table finder to use for parsing the tables.
                If None, defauts to a TableFinder with default parameters.
        """
        super().__init__()
        self.add_headers = add_headers
        self.extract_tables = extract_tables
        self.use_ocr = use_ocr
        self.ocr_language = ocr_language
        self.body_line_spacing = body_line_spacing
        self._configured_body_line_spacing = body_line_spacing  # preserved for cleanup reset
        self.table_finder = table_finder

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
        self.filepath = filepath
        if Path(filepath).suffix.lower() != ".pdf":
            raise PdfParserException("Only .pdf files can be passed to PdfParser.")
        self.document = pymupdf.open(filepath, filetype="pdf")
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
        self.document = pymupdf.open(stream=string, filetype="pdf")
        return self._parse_and_export(page_start, page_end)

    def _parse_and_export(self, page_start: int, page_end: int | None) -> MarkdownDoc:
        """Shared implementation for parse_file and parse_string.
        Runs the parse pipeline and guarantees the document is closed on exit.
        """
        try:
            self._set_page_range(page_start, page_end)
            self._parse_document()
            return self.to_markdown_doc()
        finally:
            self._document.close()
            self._document = None

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
        self.spans = self._create_spans()
        if not self.spans or all(span.is_header_footer for span in self.spans):
            raise TextNotFoundException(
                'No text content found in document. You may want to set use_ocr="always".'
            )
        self.tables = self.get_tables() if self.extract_tables else []
        self.spans = self._flag_table_spans(self.spans)
        self.lines = PdfParser._create_lines(self.spans)
        self.blocks = self._create_blocks(self.lines)
        self._set_document_specifications()
        self._flag_footnotes(self.spans)
        self.main_title = self._get_document_main_title()
        self.toc = self.get_toc() if self.add_headers else []

    def check_ocr_config_is_valid(self) -> None:
        """Check that the OCR configuration is valid."""
        tessdata_location = os.environ.get("TESSDATA_PREFIX")
        if not tessdata_location:
            raise PdfParserException(
                'To use OCR, the "TESSDATA_PREFIX" must be set as environment variable in order to locate traineddata files. For more info see https://pymupdf.readthedocs.io/en/latest/installation.html#enabling-integrated-ocr-support\nYou may otherwise want to deactivate OCR : PdfParser(use_ocr="never").',
            )
        language_list = self.ocr_language.split("+")
        for lang in language_list:
            if not os.path.exists(
                os.path.join(tessdata_location, f"{lang}.traineddata")
            ):
                raise PdfParserException(
                    f"Tesseract's {lang}.traineddata file not found at {tessdata_location}. You might need to download the corresponding file from https://github.com/tesseract-ocr/tessdata and place it in {tessdata_location}",
                )

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
        for page in self.document.pages(start=self.page_start, stop=self.page_end):  # type: ignore : missing typing in pymupdf -> document.pages() : generator[Page]
            match self.use_ocr:
                case "always":
                    textpage: pymupdf.TextPage = page.get_textpage_ocr(  # type: ignore : missing typing in pymupdf
                        language=self.ocr_language, dpi=72, full=False
                    )
                case "auto":
                    textpage: pymupdf.TextPage = page.get_textpage()  # type: ignore : missing typing in pymupdf
                    page_spans = PdfParser._extract_spans_from_textpage(
                        textpage, page.number  # type: ignore : missing typing in pymupdf -> page.number: int
                    )
                    if page_spans:
                        spans.extend(page_spans)
                        continue
                    else:
                        textpage: pymupdf.TextPage = page.get_textpage_ocr(  # type: ignore : missing typing in pymupdf
                            language=self.ocr_language, dpi=72, full=False
                        )
                case "never":
                    textpage: pymupdf.TextPage = page.get_textpage()  # type: ignore : missing typing in pymupdf
            spans.extend(PdfParser._extract_spans_from_textpage(textpage, page.number))  # type: ignore : missing typing in pymupdf -> page.number: int

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
        A span is considered a header/footer if spans with the same vertical
        band (y0 rounded to 5 pts) and font size appear on more than 33% of pages.
        This catches varying elements like page numbers that share y-position and
        font size but differ in text or exact x position.

        Args:
            spans (list[TextSpan]): the list of spans with attribute is_header_footer updated.
        """
        if self.document.page_count <= 2:  # type: ignore : missing typing in pymupdf | document.page_count : int
            return spans

        # Map (y-band, fontsize) -> set of pages where it appears
        sig_pages: defaultdict[tuple, set] = defaultdict(set)
        for span in spans:
            sig = (round(span.bbox.y0 / 5) * 5, span.fontsize)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            sig_pages[sig].add(span.page)

        header_footer_sigs = {
            sig
            for sig, pages in sig_pages.items()
            if len(pages) > self.document.page_count / 3  # type: ignore : missing typing in pymupdf | document.page_count : int
        }
        for span in spans:
            sig = (round(span.bbox.y0 / 5) * 5, span.fontsize)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            span.is_header_footer = sig in header_footer_sigs

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
        page_orientation_counts: defaultdict[int, Counter] = defaultdict(Counter)
        for span in spans_to_merge:
            page_orientation_counts[span.page][span.orientation] += 1
        page_dominant_orientation: dict[int, tuple] = {
            page: counts.most_common(1)[0][0]
            for page, counts in page_orientation_counts.items()
        }
        spans_to_merge = [
            span for span in spans_to_merge
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
            float: the value of the linespace.
        """
        # Focus on the most common fontsize so that list items, titles, or footnotes
        # with different fontsizes do not skew the body linespacing estimate.
        fontsize_counts = Counter(line.fontsize for line in lines if not line.is_empty)
        body_fontsize = fontsize_counts.most_common(1)[0][0] if fontsize_counts else None

        linespace_counts = Counter(
            round(curr_line.bbox.y0 - prev_line.bbox.y1, 1)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            for curr_line, prev_line in zip(lines[1:], lines[:-1])
            # Negative spacings occur between columns in multi-column layouts; skip them
            # as they would corrupt the linespace estimate used for block merging.
            if curr_line.bbox.y0 >= prev_line.bbox.y0  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            and (
                body_fontsize is None
                or (prev_line.fontsize == body_fontsize and curr_line.fontsize == body_fontsize)
            )
        )

        if not linespace_counts:
            # Fallback: use all lines if no body-fontsize pairs were found
            linespace_counts = Counter(
                round(curr_line.bbox.y0 - prev_line.bbox.y1, 1)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                for curr_line, prev_line in zip(lines[1:], lines[:-1])
                if curr_line.bbox.y0 >= prev_line.bbox.y0  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            )

        return max(linespace_counts, key=linespace_counts.get)

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

    def cleanup_memory(self) -> None:
        """Cleans up memory by reseting all objects created to parse the document."""
        if self._document is not None:
            self._document.close()
            self._document = None
        self.filepath = None
        self.page_start = 0
        self.page_end = None
        self.spans = []
        self.lines = []
        self.blocks = []
        self.tables = []
        self.toc = []
        self.main_title = ""
        self.document_fontsizes = []
        self.main_body_fontsizes = []
        self.main_body_is_bold = False
        # restore the user-configured value; auto-detected value is no longer valid
        self.body_line_spacing = self._configured_body_line_spacing
