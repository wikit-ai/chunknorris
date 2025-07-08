import os
from collections import Counter, defaultdict
from itertools import groupby
from math import isclose
from pathlib import Path
from typing import Literal

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

    table_finder: TableFinder = TableFinder()
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
        self.add_headers = add_headers
        self.extract_tables = extract_tables
        self.use_ocr = use_ocr
        self.ocr_language = ocr_language
        self.body_line_spacing = body_line_spacing
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
        self._set_page_range(page_start, page_end)

        self._parse_document()

        return self.to_markdown_doc()

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
        self._set_page_range(page_start, page_end)

        self._parse_document()

        return self.to_markdown_doc()

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
        self.main_title = self._get_document_main_title()
        self.toc = self.get_toc() if self.add_headers else []

    def check_ocr_config_is_valid(self):
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
        page_dict: dict[str, str] = textpage.extractDICT()  # type: ignore : missing typing in pymupdf

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
        page_tables = defaultdict(list[pymupdf.Rect])
        for table in self.tables:
            page_tables[table.page].append(table.bbox)

        for span in spans:
            span.isin_table = any(
                rect.contains(span.origin) for rect in page_tables[span.page]  # type: ignore : missing typing in pymupdf | Rect.contains(x) : bool
            )

        return spans

    def _flag_headers_footers(self, spans: list[TextSpan]) -> list[TextSpan]:
        """Flags spans that are headers and footers (inplace)
        We consider that if a bbox is present at the same place on a page
        on more that 33% of the pages of the document, it is a header or footer.
        Process:
        - Count the bbox locations of all spans.
        - Remove spans having bbox location count superior to document's page count / 3

        Args:
            spans (TextSpan): the list of spans with attribute is_header_footer updated.
        """
        if not self.document.page_count > 2:  # type: ignore : missing typing in pymupdf | document.page_count : int
            return spans

        bbox_location_counts = Counter((span.bbox) for span in spans)
        header_footer_bboxes = {
            bbox: count
            for bbox, count in bbox_location_counts.items()
            if count > self.document.page_count / 3  # type: ignore : missing typing in pymupdf | document.page_count : int
        }
        for span in spans:
            span.is_header_footer = span.bbox in header_footer_bboxes

        return spans

    @staticmethod
    def _create_lines(spans: list[TextSpan]) -> list[TextLine]:
        """Consolidate the consecutive spans by grouping them together
        in a TextLine when possible if they belong to the same line.
        Spans can be merged if:
        - they do not belong to table or header/footer
        - they have the same y positions
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
        # group spans by page
        spans_grouped_per_page = (
            list(spans_on_page)
            for _, spans_on_page in groupby(spans_to_merge, key=lambda span: span.page)
        )
        for spans_on_page in spans_grouped_per_page:
            buffer = [spans_on_page[0]]
            for span in spans_on_page[1:]:
                if isclose(span.origin.y, buffer[-1].origin.y, abs_tol=3) or span.is_superscripted:  # type: ignore : missing typing in pymupdf | Point.y : float
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
        linespace_counts = Counter(
            (
                round(curr_line.bbox.y0 - prev_line.bbox.y1, 1)  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                for curr_line, prev_line in zip(lines[1:], lines[:-1])
            )
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
                or line.bbox.y0 - self.body_line_spacing - 2 > buffer[-1].bbox.y1  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                or line.bbox.y1 <= buffer[-1].bbox.y0  # type: ignore : missing typing in pymupdf | Rect.y0 : float
            ):  # type: ignore : missing typing in pymupdf | Rect.y0 : float
                blocks.append(TextBlock(buffer))
                buffer = [line]
            # Two consecutive lines belong to the same block
            else:
                buffer.append(line)
        blocks.append(TextBlock(buffer))

        return blocks

    def cleanup_memory(self):
        """Cleans up memory by reseting all objects created to parse the document."""
        self.document.close()
        self._document = None
        self.filepath = None
        self.page_start = 0
        self.page_end = None
        self.spans = []
        self.lines = []
        self.blocks = []
        self.tables = []
        self.main_title = ""
        self.document_fontsizes = []
        self.main_body_fontsizes = []
        self.main_body_is_bold = False
