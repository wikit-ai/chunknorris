from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from itertools import groupby
from multiprocessing import cpu_count
from operator import attrgetter
from typing import TYPE_CHECKING, Any

import pymupdf  # type: ignore : no stubs

from chunknorris.decorators.decorators import timeit

from .components import TextSpan
from .components_tables import Cell, PdfTable, TableFinder
from .utils import PdfParserState


if TYPE_CHECKING:
    from .components_tables import TableFinder


def _extract_tables_from_page(args: tuple[bytes | str, int, list[TextSpan], dict[str, Any], bool]) -> list[PdfTable]:
    """Worker function to extract tables from a single page.

    This function is designed to be called in a separate process.
    It reopens the document to work around PyMuPDF's thread-safety limitations.

    Args:
        args: tuple containing (filepath_or_bytes, page_num, spans_on_page, table_finder_params, is_bytes)

    Returns:
        list[PdfTable]: tables found on this page
    """
    filepath_or_bytes, page_num, spans_on_page, table_finder_params, is_bytes = args

    try:
        # Reopen document in worker process (required for multiprocessing with PyMuPDF)
        if is_bytes:
            doc = pymupdf.open(stream=filepath_or_bytes, filetype="pdf")
        else:
            doc = pymupdf.open(filepath_or_bytes)
        page = doc.load_page(page_num)

        # Recreate table_finder with the same parameters
        table_finder = TableFinder(**table_finder_params)

        # Extract tables on this page
        tables_on_page = table_finder.build_tables(page)
        page_tables = []

        for _, _, tab_cells in tables_on_page:
            if tab_cells.shape[0] == 1:  # type: ignore : missing typing in pymupdf
                continue  # only one cell -> not a table

            cells = _get_table_cells_static(tab_cells, spans_on_page)
            # if at least 50% of cells contain a span
            if sum(bool(cell.spans) for cell in cells) / len(cells) > 0.5:
                page_tables.append(PdfTable(cells, page_num))  # type: ignore : missing typing in pymupdf

        doc.close()
        return page_tables
    except Exception as e:
        # Log error and return empty list to avoid crashing entire process
        import logging
        logging.error(f"Error extracting tables from page {page_num}: {e}")
        return []


def _get_table_cells_static(
    raw_cells: list[pymupdf.Rect], spans_on_page: list[TextSpan]
) -> list[Cell]:
    """Static version of _get_table_cells for use in multiprocessing.

    Args:
        raw_cells (list[pymupdf.Rect]): a list of rects that are cell of a table.
        spans_on_page (list[TextSpan]): a list of spans that are on the same page of the table.

    Returns:
        list[Cell]: the cells with their bound spans
    """
    cells: list[Cell] = []
    for cell_coords in raw_cells:
        cell = Cell(*cell_coords)
        spans_to_bind: list[TextSpan] = []
        for span in spans_on_page:
            small_bbox = PdfTableExtraction._get_smaller_bbox(span.bbox)
            # if the cell contains the span -> bind span to cell
            if cell.contains(small_bbox):  # type: ignore : missing typing in pymupdf
                spans_to_bind.append(span)
            # elif cell intersects the span -> span is on multiple cells -> create new splitted span
            elif cell.intersects(small_bbox):  # type: ignore : missing typing in pymupdf
                splitted_span = PdfTableExtraction._split_span(cell, span)
                spans_to_bind.append(splitted_span)

        cell.spans = spans_to_bind
        cells.append(cell)

    return cells


class PdfTableExtraction(PdfParserState):
    """Tool that groups methods related to extraction of the tables of a pdf.
    Meant to be as inerited class PdfParser(PdfTableExtraction) as it uses some of
    the attributes of PdfParser, such as self.spans and self.document
    """

    @timeit
    def get_tables(self) -> list[PdfTable]:
        """Parses the table of the document. For this to work, tables
        must have visible "lines".

        Returns:
            list[PdfTable]: the list of tables in the pdf.
        """
        spans_per_page = {
            page: list(spans_on_page)
            for page, spans_on_page in groupby(self.spans, key=lambda span: span.page)
        }

        # Determine max_workers: None means auto-detect based on page count and threshold
        if self.table_extraction_max_workers is None:
            if self.document.page_count >= self.table_extraction_multiproc_page_thresh:  # type: ignore page_count -> int
                max_workers = cpu_count()
            else:
                max_workers = 1  # Sequential processing
        else:
            max_workers = self.table_extraction_max_workers

        if max_workers <= 1:
            return self._get_tables_sequential(spans_per_page)

        return self._get_tables_parallel(spans_per_page, max_workers)

    def _get_tables_sequential(
        self, spans_per_page: dict[int, list[TextSpan]]
    ) -> list[PdfTable]:
        """Sequential table extraction (original implementation).

        Args:
            spans_per_page: Dictionary mapping page numbers to spans on that page

        Returns:
            list[PdfTable]: the list of tables in the pdf.
        """
        tables = []
        for page in self.document.pages(start=self.page_start, stop=self.page_end):  # type: ignore : missing typing in pymupdf -> document.pages() : generator[Page]
            tables_on_page = self.table_finder.build_tables(page)
            for _, _, tab_cells in tables_on_page:
                if page.number not in spans_per_page or tab_cells.shape[0] == 1:  # type: ignore : missing typing in pymupdf -> Page.number -> int
                    continue  # no spans available, or only one cell -> not a table
                cells = self._get_table_cells(tab_cells, spans_per_page[page.number])  # type: ignore : missing typing in pymupdf -> Page.number -> int
                # if at least 50% of cells contain a span
                if sum(bool(cell.spans) for cell in cells) / len(cells) > 0.5:
                    tables.append(PdfTable(cells, page.number))  # type: ignore : missing typing in pymupdf -> Page.number -> int

        return sorted(tables, key=attrgetter("order"))

    def _get_tables_parallel(
        self, spans_per_page: dict[int, list[TextSpan]], max_workers: int
    ) -> list[PdfTable]:
        """Parallel table extraction using multiprocessing.

        Args:
            spans_per_page: Dictionary mapping page numbers to spans on that page
            max_workers: Maximum number of worker processes

        Returns:
            list[PdfTable]: the list of tables in the pdf.
        """
        # Prepare table_finder parameters for pickling
        table_finder_params = {
            "snap_tolerance": self.table_finder.snap_tolerance,
            "line_width_threshold": self.table_finder.line_width_threshold,
        }

        # Determine whether to use filepath or document bytes
        filepath_or_bytes = (
            self.filepath if self.filepath is not None else self.document_bytes
        )
        is_bytes = self.filepath is None

        # Prepare arguments for each page
        page_args = []
        for page_num in range(self.page_start, self.page_end):  # type: ignore : page_end is validated in parser
            if page_num in spans_per_page:
                page_args.append(
                    (
                        filepath_or_bytes,
                        page_num,
                        spans_per_page[page_num],
                        table_finder_params,
                        is_bytes,
                    )
                )

        # Process pages in parallel
        tables = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks and use as_completed for better parallelism
            futures = [executor.submit(_extract_tables_from_page, args) for args in page_args]
            for future in as_completed(futures):
                tables.extend(future.result())

        return sorted(tables, key=attrgetter("order"))

    def _get_table_cells(
        self, raw_cells: list[pymupdf.Rect], spans_on_page: list[TextSpan]
    ) -> list[Cell]:
        """From a cells detected by the TableFinder,
        builds a list of Cell objects and binds each
        of them the spans that they contain.

        From this we want to build a list of "Cell" objects
        and binds them their corresponding text.

        Args:
            raw_cells (list[pymupdf.Rect]): a list of rects that are cell of a table.
            spans_on_page (list[TextSpan]): a list of spans that are on the same page of the table.
        """
        return _get_table_cells_static(raw_cells, spans_on_page)

    @staticmethod
    def _get_smaller_bbox(bbox: pymupdf.Rect, offset: float = 3) -> pymupdf.Rect:
        """Considering a pymupdf.Rect, returns
        a smaller Rect considering the provided offset.
        Example :
            Rect(10, 10, 20 ,20) and offset=2 will return Rect(12, 12, 18, 18)

        If the resulting rectangle is invalid, returns an empty Rectangle centered.
        Example :
            Rect(10, 10, 20, 20) and offset=8 would return Rect(18, 18, 12, 12) which is invalid
            -> Instead it will return Rect(15, 15, 15, 15)

        Args:
            bbox (pymupdf.Rect): the rectangle to consider.
            offset (float): the offset to use.

        Returns:
            pymupdf.Rect : the smaller bbox
        """
        small_bbox = pymupdf.Rect(
            bbox.x0 + offset,  # type: ignore : missing typing in pymuPdf | Rect.x0 : float
            bbox.y0 + offset,  # type: ignore : missing typing in pymuPdf | Rect.y0 : float
            bbox.x1 - offset,  # type: ignore : missing typing in pymuPdf | Rect.x1 : float
            bbox.y1 - offset,  # type: ignore : missing typing in pymuPdf | Rect.y1 : float
        )
        if not small_bbox.is_valid:  # type: ignore : missing typing in pymuPdf | Rect.is_valid : bool
            return pymupdf.Rect(
                (bbox.x0 + bbox.x1) / 2,  # type: ignore : missing typing in pymuPdf : Rect.x0, Rect.y0, Rect.x1, Rect.y1 are all float
                (bbox.y0 + bbox.y1) / 2,  # type: ignore : missing typing in pymuPdf : Rect.x0, Rect.y0, Rect.x1, Rect.y1 are all float
                (bbox.x0 + bbox.x1) / 2,  # type: ignore : missing typing in pymuPdf : Rect.x0, Rect.y0, Rect.x1, Rect.y1 are all float
                (bbox.y0 + bbox.y1) / 2,  # type: ignore : missing typing in pymuPdf : Rect.x0, Rect.y0, Rect.x1, Rect.y1 are all float
            )

        return small_bbox

    @staticmethod
    def _split_span(cell: Cell, span: TextSpan) -> TextSpan:
        """Considering a cell and a span,
        splits the span (or actually creates a new one)
        with only the text contained inside the cell.

        Args:
            cell (Cell): the cell to consider.
            span (TextSpan): the span to split.

        Returns:
            TextSpan: a new span, representing the portion of the provided span
                that is inside the cell.
        """
        # Compute the amount of character that are inside the cell
        intersect = deepcopy(cell).intersect(span.bbox)  # type: ignore : missing typing in pymuPdf | Rect.intersect(r : Rect) -> bool
        x_portion_to_keep = intersect.width / span.bbox.width  # type: ignore : missing typing in pymuPdf | Rect.width : float
        n_char_to_keep = int(round(x_portion_to_keep * len(span.text), 0))
        # Determine which portion of span is in cell (left or right)
        from_left = intersect.x0 == span.bbox.x0  # type: ignore : missing typing in pymuPdf | Rect.x0 : float
        # Get text of span inside cell
        text = (
            span.text[:n_char_to_keep]
            if from_left
            else span.text[len(span.text) - n_char_to_keep :]
        )
        new_span = TextSpan(
            bbox=intersect,
            text=text,
            font=span.font,
            color=span.fontcolor,
            size=span.fontsize,
            flags=span.flags,
            ascender=span.ascender,
            descender=span.descender,
            origin=pymupdf.Point(intersect.x0, span.origin.y),  # type: ignore : missing typing in pymuPdf | Rect.x0 : float, Point.y : float
            page=span.page,
            orientation=span.orientation,
        )
        new_span.order = span.order
        new_span.link = span.link

        return new_span
