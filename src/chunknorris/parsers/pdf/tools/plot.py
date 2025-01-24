import random
from itertools import groupby
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
import pymupdf  # type: ignore : not stubs

from .components import TextBlock, TextLine, TextSpan
from .extract_tables import PdfTable
from .utils import PdfParserState


class PdfPlotter(PdfParserState):
    """Tool that groups methods related to plotting elements obtained by
    the PdfParser. Meant to be as inerited class PdfParser(PdfPlotter)

    Most methods make use of PdfParser's attributes, such as:
    self.spans, self.lines, self.blocks, self.tables and self.document.
    """

    def get_doc_to_draw_on(
        self,
    ) -> pymupdf.Document:
        """Returns a copy of current document in order to draw
        on it without altering the source document"""
        pdfdata = self.document.tobytes()  # type: ignore : missing typing in pymupdf | Document.tobytes(*args) -> bytes
        return pymupdf.open(stream=pdfdata, filetype="pdf")

    def plot_pdf(
        self,
        page_start: int | None = None,
        page_end: int | None = None,
        items_to_plot: list[Literal["span", "line", "block", "table"]] | None = None,
        dpi: int = 100,
    ) -> None:
        """Buils a plot of the pdf file.
        Plots the span's bboxes and tables grid

        Args:
            page_start (int | None): the first page to consider.
            page_end (int | None): the last page to consider.
            items_to_plot (list[str]) : the list of types of elements to plot.
                Can be any subset of ["span", "line", "block", "table"].
            dpi (int): the resolution of the generated image
        """
        page_start = page_start or self.page_start
        page_end = page_end or self.page_end
        items_to_plot = items_to_plot or ["span", "line", "block", "table"]

        doc_to_draw_on = self.get_doc_to_draw_on()

        spans_per_page: dict[int, list[TextSpan]] = PdfPlotter._get_items_per_page(
            self.spans
        )
        lines_per_page: dict[int, list[TextLine]] = PdfPlotter._get_items_per_page(
            self.lines
        )
        blocks_per_page: dict[int, list[TextBlock]] = PdfPlotter._get_items_per_page(
            self.blocks
        )
        tables_per_page: dict[int, list[PdfTable]] = PdfPlotter._get_items_per_page(
            self.tables
        )
        for page in doc_to_draw_on.pages(page_start, page_end):  # type: ignore : missing typing in pymupdf | Document.pages() -> Generator(Page)
            if "span" in items_to_plot and page.number in spans_per_page:  # type: ignore :missing typing in pymupdf Page.number : int
                for span in spans_per_page[page.number]:  # type: ignore :missing typing in pymupdf Page.number : int
                    style = PdfPlotter._get_rect_style(span)
                    page.draw_rect(span.bbox, **style, fill_opacity=0.5)  # type: ignore : missing typing in pymupdf
            if "line" in items_to_plot and page.number in lines_per_page:  # type: ignore :missing typing in pymupdf Page.number : int
                for line in lines_per_page[page.number]:  # type: ignore :missing typing in pymupdf Page.number : int
                    page.draw_rect(line.bbox, color=pymupdf.pdfcolor["black"], width=1)  # type: ignore : missing typing in pymupdf
            if "block" in items_to_plot and page.number in blocks_per_page:  # type: ignore :missing typing in pymupdf Page.number : int
                for block in blocks_per_page[page.number]:  # type: ignore :missing typing in pymupdf Page.number : int
                    page.draw_rect(  # type: ignore : missing typing in pymupdf
                        block.bbox,
                        color=pymupdf.pdfcolor["black"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str, tuple[int, int, int]]
                        width=2,
                        dashes="[3 4] 0",
                    )
            if "table" in items_to_plot and page.number in tables_per_page:  # type: ignore :missing typing in pymupdf Page.number : int
                for table in tables_per_page[page.number]:  # type: ignore :missing typing in pymupdf Page.number : int
                    for cell in table.cells:
                        page.draw_rect(cell, color=pymupdf.pdfcolor["blue"])  # type: ignore : missing typing in pymupdf
                    page.draw_rect(table.bbox, color=pymupdf.pdfcolor["navy"])  # type: ignore : missing typing in pymupdf

            PdfPlotter.show_page(page, dpi=dpi)

    @staticmethod
    def _get_items_per_page(
        items_list: list[TextSpan | TextLine | TextBlock | PdfTable],
    ) -> dict[int, list[TextSpan | TextLine | TextBlock | PdfTable]]:
        """Groups the list of items per page. Takes as input
        any list of objects that have a "page" attribute
        Return a dict of structure is {page_number : sublist_of_items, ...}

        Args:
            items_list (list[TextSpan  |  TextLine  |  TextBlock]): A list
                of items to sort by page.

        Returns:
            dict[int,list]: The map of pages to sublists of items
        """
        return {
            page: list(items_on_page)
            for page, items_on_page in groupby(items_list, key=lambda item: item.page)
        }

    @staticmethod
    def show_page(page: pymupdf.Page, dpi: int = 100) -> None:
        """
        Generates an RGB Pixmap from the page and its rectangles,
        Args:
            page: a Page object of the document with rectangles drawn on it.
            dpi: the resolution of the generated image
        """
        plt.rcParams.update({"font.size": 5})
        pix = page.get_pixmap(dpi=dpi)  # type: ignore : missing typing in pymupdf | Page.get_pixmap(*args) -> Pixmap
        img = np.ndarray([int(pix.h), int(pix.w), 3], dtype=np.uint8, buffer=pix.samples_mv)  # type: ignore : missing typing in pymupdf | Pixmap.h : int ,Pixmap.mv : memoryview
        plt.figure(dpi=dpi)  # type: ignore : missing typing in matplotlib | plt.Figure(*args) -> Figure
        _ = plt.imshow(img, extent=(0, pix.w * 72 / dpi, pix.h * 72 / dpi, 0))  # type: ignore : missing typing in matplotlib | plt.imshow(*args) -> AxesImage

    @staticmethod
    def _get_rect_style(item: TextSpan) -> dict[str, tuple[int, int, int]]:
        """Get the kwargs for styling the rectangle, such as
        edge color and face color, considering the item's attributes

        Args:
            item (TextSpan): the item to get the styling params for

        Returns:
            dict: kwargs to be passed to the Shape.draw_rect() method
        """
        if item.is_header_footer:
            return {
                "color": pymupdf.pdfcolor["red"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str | tuple[int, int, int]]
                "fill": pymupdf.pdfcolor["tomato"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str | tuple[int, int, int]]
            }
        elif item.isin_table:
            return {
                "color": pymupdf.pdfcolor["steelblue"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str | tuple[int, int, int]]
                "fill": pymupdf.pdfcolor["lightblue"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str | tuple[int, int, int]]
            }
        else:
            return {
                "color": pymupdf.pdfcolor["goldenrod"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str | tuple[int, int, int]]
                "fill": pymupdf.pdfcolor["gold"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str | tuple[int, int, int]]
            }

    def plot_drawings(
        self,
        items_to_draw: list[Literal["l", "c", "re", "qu", "p"]] | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
        dpi: int = 100,
    ):
        """Draws the raw drawings extracted from the page.
        Mainly used for debug.

        Args:
            items_to_draw (list[Literal["l", "c", "re", "qu"]], optional): the elements to draw.
                See pymupdf.get_drawing() documentation for more info.
                Defaults to None meaning all elements are drawn.
            page_start (int | None): the first page to consider.
            page_end (int | None): the last page to consider.
            dpi (int) : the resolution. Defaults to 100.
        """
        items_to_draw = items_to_draw or ["l", "c", "re", "qu", "p"]
        doc_to_draw_on = self.get_doc_to_draw_on()
        page_start = page_start or self.page_start
        page_end = page_end or self.page_end

        for page in doc_to_draw_on.pages(page_start, page_end):  # type: ignore : missing typing in pymupdf | Document.pages() -> Generator(Page)
            drawings: list[dict[str, tuple[str, tuple[Any]]]] = page.get_drawings()  # type: ignore : missing typing in pymupdf | Page.get_drawings() -> list[dict[Any]]
            for i, drawing in enumerate(drawings):
                for j, item in enumerate(drawing["items"]):
                    if not item[0] in items_to_draw:
                        continue
                    match item[0]:
                        case "l":
                            page.draw_line(*item[1:], color=(1, 0, 0.7))  # type: ignore : missing typing in pymupdf
                            page.insert_text((item[1].x, item[1].y), f"d{i}i{j}l")  # type: ignore : missing typing in pymupdf | Point.x/y -> float
                        case "c":
                            page.draw_bezier(*item[1:], color=(1, 1, 0))  # type: ignore : missing typing in pymupdf | Document.pages() -> Generator(Page)
                        case "re":
                            page.draw_rect(  # type: ignore : missing typing in pymupdf | Document.pages() -> Generator(Page)
                                item[1],
                                color=(
                                    random.random(),
                                    random.random(),
                                    random.random(),
                                ),
                            )
                            page.insert_text((item[1].x0, item[1].y0), f"d{i}i{j}r")  # type: ignore : missing typing in pymupdf
                        case "qu":
                            page.draw_quad(item[1], color=(0, 0, 1))  # type: ignore : missing typing in pymupdf
                        case "p":
                            page.draw_circle(item, 3)  # type: ignore : missing typing in pymupdf

            PdfPlotter.show_page(page, dpi=dpi)

    def plot_parsed_tables(
        self, page_start: int | None = None, page_end: int | None = None, dpi: int = 100
    ):
        """Plots a parsed table"""
        if not self.tables:
            raise ValueError(
                "No tables to be plotted. Make sure a document has been parsed."
            )
        page_start = page_start or self.page_start
        page_end = page_end or self.page_end
        doc_to_draw_on = self.get_doc_to_draw_on()
        for page in doc_to_draw_on.pages(page_start, page_end):  # type: ignore : missing typing in pymupdf | Document.pages() -> Generator(Page)
            tables = self.table_finder.build_tables(page)
            if not tables:
                continue
            for lines, intersections, cells in tables:
                color = (
                    random.uniform(0.4, 0.7),
                    random.uniform(0.4, 0.7),
                    random.uniform(0.4, 0.7),
                )
                page = PdfPlotter.draw_lines(
                    lines, page, color=[c + random.uniform(-0.1, 0.1) for c in color]
                )
                page = PdfPlotter.draw_rectangles(
                    cells, page, color=[c - 0.4 for c in color]
                )
                page = PdfPlotter.draw_points(
                    intersections, page, color=[c + 0.2 for c in color]
                )
            PdfPlotter.show_page(page, dpi=dpi)

    @staticmethod
    def draw_points(
        points_coord: list[tuple[float, float]],
        page_to_draw_on: pymupdf.Page,
        color: tuple[float, float, float] = (0, 0, 0),
    ) -> pymupdf.Page:
        """Draws a list of points on provided page"""
        for point in points_coord:
            page_to_draw_on.draw_circle(pymupdf.Point(point), 3, fill=color)  # type: ignore : missing typing in pymupdf | Point.x/y -> float

        return page_to_draw_on

    @staticmethod
    def draw_rectangles(
        rectangle_coords: list[pymupdf.Rect],
        page_to_draw_on: pymupdf.Page,
        color: tuple[float, float, float] = (0, 0, 0),
    ) -> pymupdf.Page:
        """Draws a list of rectangle on provided page"""
        for rect in rectangle_coords:
            page_to_draw_on.draw_rect(list(rect), color=color, width=2)  # type: ignore : missing typing in pymupdf | Point.x/y -> float

        return page_to_draw_on

    @staticmethod
    def draw_lines(
        lines: list[tuple[float, float, float, float]],
        page_to_draw_on: pymupdf.Page,
        color: tuple[float, float, float] = (0, 0, 0),
    ) -> pymupdf.Page:
        """Draws a list of lines on provided page"""
        for line in lines:
            page_to_draw_on.draw_line(  # type: ignore : missing typing in pymupdf | Point.x/y -> float
                (line[0], line[1]), (line[2], line[3]), color=color, width=6
            )

        return page_to_draw_on

    def plot_reading_order(
        self, page_start: int | None = None, page_end: int | None = None, dpi: int = 100
    ):
        """Plots the detected reading order of the blocks"""
        page_start = page_start or self.page_start
        page_end = page_end or self.page_end
        doc_to_draw_on = self.get_doc_to_draw_on()

        blocks_per_page: dict[int, list[TextBlock]] = PdfPlotter._get_items_per_page(
            self.blocks
        )
        for page in doc_to_draw_on.pages(page_start, page_end):  # type: ignore : missing typing in pymupdf | Document.pages() -> Generator(Page)
            if not page.number in blocks_per_page:  # type: ignore : missing typing in pymupdf | Page.number -> int
                continue

            prev_block_location = (0, 0)
            for block in blocks_per_page[page.number]:
                block_location = (
                    block.bbox.x1 - (block.bbox.x1 - block.bbox.x0) / 2,  # type: ignore : missing typing in pymupdf
                    block.bbox.y1 - (block.bbox.y1 - block.bbox.y0) / 2,  # type: ignore : missing typing in pymupdf
                )
                page.draw_rect(list(block.bbox), fill=(0.6, 0.6, 0.8), width=2)  # type: ignore : missing typing in pymupdf
                page.insert_text(block_location, f"{block.order}", fontsize=30)  # type: ignore : missing typing in pymupdf
                page.draw_line(prev_block_location, block_location, color=(0.8, 0.3, 0.3), width=4)  # type: ignore : missing typing in pymupdf
                page.draw_circle(block_location, 6, fill=(0.5, 0.2, 0.2), color=(0.1, 0.1, 0.1))  # type: ignore : missing typing in pymupdf
                prev_block_location = block_location

            PdfPlotter.show_page(page, dpi=dpi)
