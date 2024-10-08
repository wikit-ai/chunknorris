from itertools import groupby
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pymupdf  # type: ignore : not stubs

from .utils import PdfParserState
from .extract_tables import PdfTable
from .components import TextSpan, TextLine, TextBlock


class PdfPlotter(PdfParserState):
    """Tool that groups methods related to plotting elements obtained by
    the PdfParser. Meant to be as inerited class PdfParser(PdfPlotter)

    Most methods make use of PdfParser's attributes, such as:
    self.spans, self.lines, self.blocks, self.tables and self.document.
    """

    def plot_pdf(
        self,
        items_to_plot: list[Literal["span", "line", "block", "table"]] | None = None,
        dpi: int = 100,
    ) -> None:
        """Buils a plot of the pdf file.
        Plots the span's bboxes and tables grid

        Args:
            items_to_plot (list[str]) : the list of types of elements to plot.
                Can be any subset of ["span", "line", "block", "table"].
            dpi (int): the resolution of the generated image
        """
        if not items_to_plot:
            items_to_plot = ["span", "line", "block", "table"]

        ## copy pdf inmemory to draw on it
        pdfdata = self.document.tobytes()  # type: ignore : missing typing in pymupdf | Document.tobytes(*args) -> bytes
        doc_to_draw_on = pymupdf.open(stream=pdfdata, filetype="pdf")

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

        for page_n in spans_per_page.keys():
            page = doc_to_draw_on.load_page(page_n)  # type: ignore : missing typing in pymupdf | Document.load_page(page_id: int) -> Page
            if "span" in items_to_plot and page_n in spans_per_page:
                for span in spans_per_page[page_n]:
                    style = PdfPlotter._get_rect_style(span)
                    page.draw_rect(span.bbox, **style, fill_opacity=0.5)  # type: ignore : missing typing in pymupdf
            if "line" in items_to_plot and page_n in lines_per_page:
                for line in lines_per_page[page_n]:
                    page.draw_rect(line.bbox, color=pymupdf.pdfcolor["black"], width=1)  # type: ignore : missing typing in pymupdf
            if "block" in items_to_plot and page_n in blocks_per_page:
                for block in blocks_per_page[page_n]:
                    page.draw_rect(  # type: ignore : missing typing in pymupdf
                        block.bbox,
                        color=pymupdf.pdfcolor["black"],  # type: ignore : missing typing in pymupdf | pymupdf.pdfcolor : dict[str, tuple[int, int, int]]
                        width=2,
                        dashes="[3 4] 0",
                    )
            if "table" in items_to_plot and page_n in tables_per_page:
                for table in tables_per_page[page_n]:
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
