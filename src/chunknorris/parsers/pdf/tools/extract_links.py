from itertools import groupby

import numpy as np
import numpy.typing as npt
import pymupdf  # type: ignore | no stub files

from .components import Link, TextSpan
from .utils import PdfParserState


class PdfLinkExtraction(PdfParserState):
    """Class intended to be used to extract the links from the document
    and bind them to the corresponding spans.
    Intended to be a component inherited by pdfParser => PdfParser(PdfLinkExtraction)
    """

    def _bind_links_to_spans(self, spans: list[TextSpan]) -> list[TextSpan]:
        """In a pdf, links are just an invisible clickable box
        layered on top of a span.
        This method gets the links of the pdf
        and binds them to their corresponding span.

        Args:
            spans (list[TextSpan]): the list of spans

        Returns:
            list[TextSpan]: the list of spans, with the "link" and "has_link" attributes updated
        """
        spans_per_page_map = {
            page_n: list(spans_on_page)
            for page_n, spans_on_page in groupby(spans, key=lambda span: span.page)
        }
        links_per_page_map: dict[int, list[Link]] = {
            page.number: [  # type: ignore | missing typing in pymupdf: Page.number : int
                Link(uri=link["uri"], bbox=link["from"])
                for link in page.links(kinds=(pymupdf.LINK_URI,))  # type: ignore | missing typing in pymupdf: Page.links() -> list[dict[str, str]]
            ]
            for page in self.document.pages(self.page_start, self.page_end)  # type: ignore | missing typing in pymupdf: Document.Pages() -> Generator(Page)
        }
        for page_n, links_on_page in links_per_page_map.items():
            if not links_on_page or not page_n in spans_per_page_map:
                continue  # No links to bind on that page, or no spans to bind links to
            links_bboxes = np.array([link.bbox for link in links_per_page_map[page_n]])
            spans_bboxes = np.array([span.bbox for span in spans_per_page_map[page_n]])
            intersection_areas = PdfLinkExtraction.calculate_intersection_areas(
                spans_bboxes, links_bboxes
            )  # 2D matrix of intersection areas. Shape : (n_spans, n_links)
            for i in range(intersection_areas.shape[1]):
                corresponding_span_idx = (
                    PdfLinkExtraction._get_span_corresponding_to_link(
                        intersection_areas[:, i]
                    )
                )
                if corresponding_span_idx is not None:
                    spans_per_page_map[page_n][corresponding_span_idx].link = (
                        links_per_page_map[page_n][i]
                    )

        return spans

    @staticmethod
    def calculate_intersection_areas(
        spans_bboxes: npt.NDArray[np.float32], links_bboxes: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Calculates the intersection areas of each span bbox
        respective to each link bbox.

        Args:
            spans_bboxes (npt.NDArray[np.float32]): A 2D array representing the bbox coordinates of all  the spans' bboxes.
                Expected to be of shape (n_spans_bboxes, 4).
            links_bboxes (npt.NDArray[np.float32]):  A 2D array representing the bbox coordinates of all the links' bboxes.
                Expected to be of shape (n_links_bboxes, 4).

        Returns:
            npt.NDArray[np.float32]: A 2D array of shape (n_links_bboxes, n_spans_bboxes) with each value
                representing the intersection area of the ith span's bbox with jth link's bbox.
        """
        # Extract the coordinates for the intersection calculation
        x11, y11, x12, y12 = (
            spans_bboxes[:, 0][:, None],
            spans_bboxes[:, 1][:, None],
            spans_bboxes[:, 2][:, None],
            spans_bboxes[:, 3][:, None],
        )
        x21, y21, x22, y22 = (
            links_bboxes[:, 0],
            links_bboxes[:, 1],
            links_bboxes[:, 2],
            links_bboxes[:, 3],
        )

        # Calculate the coordinates of the intersection rectangle
        x_left = np.maximum(x11, x21)
        y_top = np.maximum(y11, y21)
        x_right = np.minimum(x12, x22)
        y_bottom = np.minimum(y12, y22)

        # Calculate intersection areas
        inter_width = np.maximum(0, x_right - x_left)
        inter_height = np.maximum(0, y_bottom - y_top)
        intersection_areas = inter_width * inter_height

        return intersection_areas

    @staticmethod
    def _get_span_corresponding_to_link(
        intersect_areas: npt.NDArray[np.float16],
    ) -> int | None:
        """Given an array of intersect areas, find the idx of the spans
        that corresponds to the link. The array must be of shape (n_spans,).

        To find the span a link is bound to, we consider the area of the
        intersection of the link's bbox and the span's bbox.
        Two different situations:
        - 1) there is only one span with a high bbox intersection value with the link
            => this span is the one of the link
        - 2) there are multiple spans with a high bbox intersection.
            => for some reason, the span corresponding to the link is not the one
            with the biggest bbox intersection area, but the one with the second biggest.
        Args:
            intersect_areas (npt.NDArray[np.float16]): an array of intersections area of a link with
                all spans on the same page.

        WARNING : MAY return None if no span with bbox intersection with the link's bbox has been found

        Returns:
            int: the index of the corresponding span in the list
        """
        # Build a list of (span_idx, span/link_intersect_area) tuples, sorted by intersect area in descending order
        idx_area_tuples = list(
            zip(np.argsort(-intersect_areas), -np.sort(-intersect_areas))
        )

        idx_area_tuples = [item for item in idx_area_tuples if item[1] > 0]
        if not idx_area_tuples:
            return None  # no span with intersection with link

        best_idx, best_area = idx_area_tuples[0]
        if len(idx_area_tuples) == 1:
            return best_idx
        elif len(idx_area_tuples) > 1:
            if best_area / 2 > idx_area_tuples[1][1]:
                return best_idx
            else:
                idx_area_tuples = [
                    item for item in idx_area_tuples if item[1] < best_area
                ]
                if idx_area_tuples:
                    return idx_area_tuples[0][0]
                return None
