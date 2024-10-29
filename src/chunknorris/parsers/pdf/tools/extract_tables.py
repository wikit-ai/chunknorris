from itertools import groupby
from operator import attrgetter
from copy import deepcopy

import pymupdf  # type: ignore : no stubs

from .components import Cell, TextSpan, PdfTable
from .utils import PdfParserState


class PdfTableExtraction(PdfParserState):
    """Tool that groups methods related to extraction of the tables of a pdf.
    Meant to be as inerited class PdfParser(PdfTableExtraction) as it uses some of
    the attributes of PdfParser, such as self.spans and self.document
    """

    def get_tables(self) -> list[PdfTable]:
        """Parses the table of the document. For this to work, tables
        must have visible "lines".

        Returns:
            PdfTable: the list of tables in the pdf.
        """
        spans_per_page = {
            page: list(spans_on_page)
            for page, spans_on_page in groupby(self.spans, key=lambda span: span.page)
        }
        # get tables on all pages
        tables = []
        for page in self.document.pages(start=self.page_start, stop=self.page_end):  # type: ignore : missing typing in pymupdf -> document.pages() : generator[Page]
            raw_tables: pymupdf.table.TableFinder = page.find_tables(  # type: ignore : missing typing in pymupdf -> Page.find_tables() -> pymupdf.TableFinder
                horizontal_strategy="lines_strict",
                vertical_strategy="lines_strict",
            ).tables
            for raw_table in raw_tables:  # type: ignore : missing typing in pymupdf -> TableFinder.tables  : list[pymupdf.table.Table]
                raw_table = PdfTableExtraction.sanitize_table(raw_table)
                cells = self._get_table_cells(raw_table, spans_per_page[page.number])  # type: ignore : missing typing in pymupdf -> Page.number -> int
                # if the table contains at least 1 span
                if any(cell.spans for cell in cells):
                    tables.append(PdfTable(cells, page.number))  # type: ignore : missing typing in pymupdf -> Page.number -> int

        return sorted(tables, key=attrgetter("order"))

    @staticmethod
    def sanitize_table(
        table: pymupdf.table.Table, wordcount_threshold: int = 60
    ) -> pymupdf.table.Table:
        """Sanitize the table by removing columns that are
        likely to be false detection. Column is considered
        a wrong detection if:
        - all cells are empty
        - one cell as more words than wordcount_threshold

        Args:
            table (pymupdf.table.Table): a pymupdf table
            wordcount_threshold (int) : columns that have at least one cell that contains
                more words than wordcount_threshold will be discarded. Defaults to 60.
        """
        df = table.to_pandas().fillna("")  # type: ignore : missing typing in pymupdf table.to_pandas() -> pandas.DataFrame
        # Get the idx of cols that only have empty cells
        idx_of_cols_to_remove_empty = [
            i for i, col in enumerate(df.columns) if (df[col] != "").sum() == 0  # type: ignore : missing typing in pandas sum()
        ]
        # Get the idx of cols that have at least on cell with a lonf text
        ## Set the header as last raow to include it in word count
        df.loc[-1] = df.columns
        ## Count words in each cell
        wordcount_per_cell = df.map(lambda x: len(str(x).split()))  # type: ignore : missing typing in pandas map()
        idx_of_cols_to_remove_wordcount = [
            i
            for i, col_name in enumerate(wordcount_per_cell.columns)
            if (wordcount_per_cell[col_name] > wordcount_threshold).any()  # type: ignore : missing typing in pandas any()
        ]
        # Get all the x positions of the columns that must be removed
        idx_of_cols_to_remove = set(
            idx_of_cols_to_remove_empty + idx_of_cols_to_remove_wordcount
        )
        ## Get the x0 positions of the columns
        cols_x0_pos = list(set(bbox[0] for bbox in table.cells))
        pos_to_discard = [cols_x0_pos[i] for i in idx_of_cols_to_remove]
        # Remove all cells corresponding to those columns
        table.cells = [
            cell
            for cell in table.cells
            if cell is not None and cell[0] not in pos_to_discard
        ]
        table.header.cells = [  # type: ignore : missing typing in pymupdf header : pymupdf.table.TableHeader
            cell
            for cell in table.header.cells  # type: ignore : missing typing in pymupdf header : pymupdf.table.TableHeader
            if cell is not None and cell[0] not in idx_of_cols_to_remove
        ]
        table.header.names = [  # type: ignore : missing typing in pymupdf header : pymupdf.table.TableHeader
            name
            for i, name in enumerate(table.header.names)  # type: ignore : missing typing in pymupdf header : pymupdf.table.TableHeader
            if i not in idx_of_cols_to_remove
        ]

        return table

    def _get_table_cells(
        self, raw_table: pymupdf.table.Table, spans_on_page: list[TextSpan]
    ) -> list[Cell]:
        """From a pymupdf table,
        builds a list of Cell objects and binds each
        of them the spans that they contain.

        In pymupdf, the "cell" attribute of the Table class
        is just a list of tuple representing (x0, y0, x1, y1)
        coordinates.
        From this we want to build a list of "Cell" objects
        and binds them their corresponding text.

        Args:
            raw_table (pymupdf.table.Table): a table directly extracted from pymupdf's find_table() method.
            spans_on_page (list[TextSpan]): a list of spans that are on the same page of the table.
        """
        cells: list[Cell] = []
        for cell_coords in raw_table.cells:
            cell = Cell(*cell_coords)
            spans_to_bind: list[TextSpan] = []
            for span in spans_on_page:
                small_bbox = PdfTableExtraction._get_smaller_bbox(span.bbox)
                # if the cell contains the span -> bind span to cell
                if cell.contains(small_bbox):  # type: ignore : missing typing in pymupdf -> Rect.contains(r: Point | Rect) -> bool
                    spans_to_bind.append(span)
                # elif cell intersects the span -> span is on multiple cells -> create new splitted span
                elif cell.intersects(small_bbox):  # type: ignore : missing typing in pymupdf -> Rect.intersects(r: Rect) -> bool
                    splitted_span = PdfTableExtraction._split_span(cell, span)
                    spans_to_bind.append(splitted_span)

            cell.spans = spans_to_bind
            cells.append(cell)

        return cells

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
        )
        new_span.order = span.order

        return new_span
