import re
from operator import attrgetter
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
import pymupdf  # type: ignore | No stubs

from .components import TextSpan


class Cell(pymupdf.Rect):
    """A cell object. It inherit
    the pymupdf.Rect class but has PdfParser's spans
    bound to it
    """

    spans: list[TextSpan]

    def __init__(self, x0: float, y0: float, x1: float, y1: float) -> None:
        super().__init__(x0, y0, x1, y1)  # type: ignore : missing typing in pymuPdf : Rect.x0, Rect.y0, Rect.x1, Rect.y1 are all float
        # State
        self.spans = []


class PdfTable:
    """This class is intended to be used to parse the table of the document
    Note that pyMuPdf already implements a "Table" class.
    Though it has several issues :
    - wrongly parsed cell text (artifacts)
    - bad handling of merged cells
    - not fitting well with the mechanic of the PdfParser
    """

    cells: list[Cell]
    page: int

    def __init__(self, cells: list[Cell], page: int) -> None:
        """Initialize Table

        Args:
            cells (list[Cell]): a list of Cell object that are part of the table
            page (int): the page number the table belongs to
        """
        self.cells = cells
        self.page = page

    @property
    def bbox(self) -> pymupdf.Rect:
        return pymupdf.Rect(
            min(self.cells, key=lambda cell: cell.x0).x0,  # type: ignore : missing typing in pymuPdf | Rect.x0 : float
            min(self.cells, key=lambda cell: cell.y0).y0,  # type: ignore : missing typing in pymuPdf | Rect.y0 : float
            max(self.cells, key=lambda cell: cell.x1).x1,  # type: ignore : missing typing in pymuPdf | Rect.x1 : float
            max(self.cells, key=lambda cell: cell.y1).y1,  # type: ignore : missing typing in pymuPdf | Rect.y1 : float
        )

    @property
    def is_header_footer(self) -> bool:
        return all(span.is_header_footer for cell in self.cells for span in cell.spans)

    @property
    def order(self) -> int:
        return min(
            (span for cell in self.cells for span in cell.spans),
            key=attrgetter("order"),
        ).order

    def get_table_grid(self) -> list[list[Cell]]:
        """Gets the grid of the table.
        As some self.cells might be merged cells, this
        method get the grid of cells as if no cells were merged

        Returns:
            list[list[Cells]] : the list of cells, organized by row
        """
        y_lines = sorted(
            list(
                set(cell.y0 for cell in self.cells)  # type: ignore : missing typing in pymuPdf | Rect.y0 : float
                | set(cell.y1 for cell in self.cells)  # type: ignore : missing typing in pymuPdf | Rect.y1 : float
            )
        )
        x_lines = sorted(
            list(
                set(cell.x0 for cell in self.cells)  # type: ignore : missing typing in pymuPdf | Rect.x0 : float
                | set(cell.x1 for cell in self.cells)  # type: ignore : missing typing in pymuPdf | Rect.x1 : float
            )
        )
        grid_cells: list[list[Cell]] = []
        for y0, y1 in zip(y_lines[:-1], y_lines[1:]):
            row_cells: list[Cell] = []
            for x0, x1 in zip(x_lines[:-1], x_lines[1:]):
                row_cells.append(Cell(x0, y0, x1, y1))
            grid_cells.append(row_cells)

        return grid_cells

    def to_pandas(self) -> pd.DataFrame:
        """Transforms this table to a pd.DataFrame

        Returns:
            pd.DataFrame : the table as dataframe
        """
        grid_cells = self.get_table_grid()
        df_constructor: list[list[str]] = []
        for grid_row in grid_cells:
            row_text: list[str] = []
            for grid_cell in grid_row:
                cell_text = ""
                for cell in self.cells:
                    if cell.contains(grid_cell):  # type: ignore : missing typing in pymuPdf | Rect.contains(r: Rect | Point) -> bool
                        for span in cell.spans:
                            cell_text += " " + span.text
                row_text.append(cell_text)
            df_constructor.append(row_text)

        df = (
            pd.DataFrame(df_constructor[1:], columns=df_constructor[0])
            .drop_duplicates()
            .dropna(axis=0, how="all")  # type: ignore | type of dropna in partially unknown
            .dropna(axis=1, how="all")  # type: ignore | type of dropna in partially unknown
        )

        return df

    def to_markdown(self) -> str:
        """Builds a markdown string from the provided table

        Returns:
            str: the markdown string
        """
        table_as_md = self.to_pandas().to_markdown(index=False)
        table_as_md = re.sub(r"\s{3,}", "  ", table_as_md)
        table_as_md = re.sub(r"-{3,}", "---", table_as_md)

        return table_as_md

    def __str__(self) -> str:
        return self.to_markdown()


class TableFinder:
    """Superseeds pymupdf's TableFinder class. Aims at being faster
    while maintaining table parsing capabilities
    """

    def __init__(self, snap_tolerance: int = 3, line_width_threshold: int = 5):
        """Init a tablefinder

        Args:
            snap_tolerance (int, optional): the tolerance threshold (in point) to consider
                two lines are intersecting or aligned. Defaults to 3.
            line_width_threshold (int, optional): natively, most lines come as a rectangle
                in the pdf, to take into account the width of the line.
                This arg specifies a threshold : all rectangle having a width below it is considered a line.
                Defaults to 5.
        """
        self.snap_tolerance = snap_tolerance
        self.line_width_threshold = line_width_threshold

    def build_tables(
        self, page: pymupdf.Page
    ) -> list[
        tuple[npt.NDArray[np.float32], npt.NDArray[np.float32], npt.NDArray[np.float32]]
    ]:
        """Method that wraps all the logic
        to parse the tables on a page of a pdf document.

        Args:
            page (pymupdf.Page): a page of a document

        Returns:
            list[tuple[npt.NDArray[np.float32], npt.NDArray[np.float32], npt.NDArray[np.float32]]]:
                Each item of the list is a tuple that contains 3 numpy arrays:
                    - coordinates of detected lines, where each row is (x1, y1, x2, y2). Shape : (n_lines, 4).
                    - coordinates of intersections between lines, where each row is (x, y). Shape : (n_intersections, 2).
                    - coordinates of cells, where each row is coordinates of rectangles as where each row is (x1, y1, x2, y2). Shape : (n_cells, 2).
        """
        lines_coordinates = self._get_table_lines(page)
        if not lines_coordinates.size:
            return []
        lines_grouped_by_table = self.group_lines_by_table(lines_coordinates)
        # tuples of (line_coord, intersections and cells) for each table. We might only need the cells later if we do not need plotting
        parsed_tables = [
            self.build_table(table_lines) for table_lines in lines_grouped_by_table
        ]
        # remove tables with no cells
        return [tab for tab in parsed_tables if tab[2].size]

    def _get_table_lines(self, page: pymupdf.Page) -> npt.NDArray[np.float32]:
        """Gets the lines that are likely to belong to a table. Proceed like so:
        - Get the drawings on the page (vectors)
        - Removes the drawings that are due to annotations (i.e. rectangles used to highlight text)
        - Convert rectangles coordinates to 4 lines coordinates
        - Remove very short lines that are likely to belong to vector designs

        Args:
            page (pymupdf.Page): the page to get the drawings from.

        Returns:
            npt.NDArray[np.float32]: an array of line coordinates of shape (n_lines, 4)
                where each row is x1, y1, x2, y2.
        """
        drawings = page.get_drawings()  # type: ignore missing typing in pymupdf
        drawings = TableFinder._remove_drawings_from_annotations(drawings, page)
        drawings = self._convert_rectangles_to_lines(drawings)
        # Get coordinates of all lines
        line_coordinates = np.array(
            [
                (item[1].x, item[1].y, item[2].x, item[2].y)
                for drawing in drawings
                for item in drawing["items"]
                if item[0] == "l"
            ]
        ).round()
        if not line_coordinates.size:
            return np.empty(shape=(0, 4))
        line_coordinates = TableFinder._filter_lines(line_coordinates)

        return line_coordinates

    @staticmethod
    def _remove_drawings_from_annotations(
        drawings: list[dict[str, Any]], page: pymupdf.Page
    ) -> list[dict[str, Any]]:
        """Removes the drawings that are likely to be due to annotations, i.e rectangles
        used to highlight text.

        Args:
            drawings (list[dict[Any]]): the drawings obtained from Page.get_drawings()
            page (pymupdf.Page): the page to get the drawings from.

        Returns:
            list[dict[Any]]: the drawings that are not due to annotations.
        """
        annotations = list(page.annots())  # type: ignore :: missing typing in pymupdf -> Page.annots() -> Generator[Annots]
        if not annotations:
            return drawings

        filtered_drawings: list[dict[str, Any]] = [
            drawing
            for drawing in drawings
            if not any(annotation.rect.contains(drawing["rect"]) for annotation in annotations)  # type: ignore :: missing typing in pymupdf -> Rect.contains() -> bool
        ]

        return filtered_drawings

    def _convert_rectangles_to_lines(
        self, drawings: list[tuple[Any]]
    ) -> list[dict[str, list[tuple[Any]]]]:
        """Converts the rectangles to lines if their width
        is below self.line_width_threshold.

        Args:
            drawings (list[tuple[Any]]): the drawings extracted from a pymupdf.Page.

        Returns:
            list[dict[str, list[tuple[Any]]]]: the drawings, same format as pumupdf.Page.get_cdrawings()'s return,
                with some rectangles converted to lines.
        """
        processed_drawings: list[dict[str, list[tuple[Any]]]] = []
        for drawing in drawings:
            drawing_items: list[tuple[Any]] = []
            for item in drawing["items"]:
                if item[0] == "re":
                    if item[1].width < self.line_width_threshold:  # type: ignore : missing typing in pymupdf rect.witdh : float
                        mid_x = (item[1].x1 - item[1].x0) / 2 + item[1].x0  # type: ignore : missing typing in pymupdf rect.x0/x1 : float
                        item = (
                            "l",
                            pymupdf.Point(mid_x, item[1].y0),  # type: ignore : missing typing in pymupdf rect.y0/y1 : float
                            pymupdf.Point(mid_x, item[1].y1),  # type: ignore : missing typing in pymupdf rect.y0/y1 : float
                        )
                    elif item[1].height < self.line_width_threshold:  # type: ignore : missing typing in pymupdf rect.height : float
                        mid_y = (item[1].y1 - item[1].y0) / 2 + item[1].y0  # type: ignore : missing typing in pymupdf rect.y0/y1 : float
                        item = (
                            "l",
                            pymupdf.Point(item[1].x0, mid_y),  # type: ignore : missing typing in pymupdf rect.x0/x1 : float
                            pymupdf.Point(item[1].x1, mid_y),  # type: ignore : missing typing in pymupdf rect.x0/x1 : float
                        )
                drawing_items.append(item)
            processed_drawings.append({"items": drawing_items})

        return processed_drawings

    @staticmethod
    def _filter_lines(
        line_coordinates: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """filter the detected lines if they might belong to tables"""
        # only keep vertical or horizontal lines
        line_coordinates = line_coordinates[
            (line_coordinates[:, 0] == line_coordinates[:, 2])
            | ((line_coordinates[:, 1] == line_coordinates[:, 3]))
        ]
        # only keep lines of minimum size 5 points
        # TODO : Determine if threshold of 5 is good or not. Maybe find dynamic threshold based on page size.
        line_coordinates = line_coordinates[
            (np.abs(line_coordinates[:, 0] - line_coordinates[:, 2]) > 5)
            | (np.abs(line_coordinates[:, 1] - line_coordinates[:, 3]) > 5)
        ]

        return line_coordinates

    def build_table(
        self, lines_coordinates: npt.NDArray[np.float32]
    ) -> tuple[
        npt.NDArray[np.float32], npt.NDArray[np.float32], npt.NDArray[np.float32]
    ]:
        """Considering lines coordinate of 1 tables,
        returns the cells of that table

        Args:
            lines_coordinates (npt.NDArray[np.float32]): Array of shape (n lines, 4) representing
                the coordinates of the lines with each row being (x0, y0, x1, y1) coordinates.

        Returns:
            tuple[npt.NDArray[np.float32], npt.NDArray[np.float32], npt.NDArray[np.float32]]]:
                Tuple that contains 3 numpy arrays:
                    - coordinates of detected lines, where each row is (x1, y1, x2, y2). Shape : (n_lines, 4).
                    - coordinates of intersections between lines, where each row is (x, y). Shape : (n_intersections, 2).
                    - coordinates of cells, where each row is coordinates of rectangles as where each row is (x1, y1, x2, y2). Shape : (n_cells, 2).
        """
        # Get intersections of lines
        intersections = self.get_line_intersections(lines_coordinates)
        if not intersections.size:
            return lines_coordinates, np.empty((0, 2)), np.empty((0, 4))
        intersections = self.normalize_table_grid(intersections)

        lines_coordinates = self._normalize_lines_grid(lines_coordinates, intersections)
        lines_coordinates = TableFinder.subdivide_lines(
            lines_coordinates, intersections
        )
        # Get cells
        cells = self._get_cells(intersections, lines_coordinates)
        if not cells.size or not TableFinder._table_sanity_check(cells):
            return lines_coordinates, intersections, np.empty((0, 4))

        return lines_coordinates, intersections, cells

    def get_line_intersections(
        self, coordinates: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """
        Find all intersection points between line segments.

        Args:
            coordinates (npt.NDArray[np.float32]): A numpy array of shape (n_lines, 4) where each row is the coordinates
                of the points of the lines like (x0, y0, x1, y1).

        Returns:
            (npt.NDArray[np.float32]): A numpy array of shape (n_intersections, 2) where each row is a the coordinates
                an intersection point between 2 segments like (x, y).
        """
        # Extract coordinates
        x1, y1, x2, y2 = self._bounding_boxes(coordinates)
        # Create matrices for pairwise combinations
        n = coordinates.shape[0]
        x1_tile = np.tile(x1, (n, 1))
        y1_tile = np.tile(y1, (n, 1))
        x2_tile = np.tile(x2, (n, 1))
        y2_tile = np.tile(y2, (n, 1))
        x3_tile = x1_tile.T
        y3_tile = y1_tile.T
        x4_tile = x2_tile.T
        y4_tile = y2_tile.T
        # Calculate denominators
        denom = (x1_tile - x2_tile) * (y3_tile - y4_tile) - (y1_tile - y2_tile) * (
            x3_tile - x4_tile
        )
        # Avoid division by zero for parallel lines
        denom[denom == 0] = np.nan
        # Calculate intersection points
        px = (
            (x1_tile * y2_tile - y1_tile * x2_tile) * (x3_tile - x4_tile)
            - (x1_tile - x2_tile) * (x3_tile * y4_tile - y3_tile * x4_tile)
        ) / denom
        py = (
            (x1_tile * y2_tile - y1_tile * x2_tile) * (y3_tile - y4_tile)
            - (y1_tile - y2_tile) * (x3_tile * y4_tile - y3_tile * x4_tile)
        ) / denom
        # Check if intersection points are within the segments
        within_segment1 = (
            (np.minimum(x1_tile, x2_tile) - self.snap_tolerance <= px)
            & (px <= np.maximum(x1_tile, x2_tile) + self.snap_tolerance)
            & (np.minimum(y1_tile, y2_tile) - self.snap_tolerance <= py)
            & (py <= np.maximum(y1_tile, y2_tile) + self.snap_tolerance)
        )
        within_segment2 = (
            (np.minimum(x3_tile, x4_tile) - self.snap_tolerance <= px)
            & (px <= np.maximum(x3_tile, x4_tile) + self.snap_tolerance)
            & (np.minimum(y3_tile, y4_tile) - self.snap_tolerance <= py)
            & (py <= np.maximum(y3_tile, y4_tile) + self.snap_tolerance)
        )
        valid_intersections = within_segment1 & within_segment2
        # Extract valid intersection points
        intersections = np.column_stack(
            (px[valid_intersections], py[valid_intersections])
        )

        return np.unique(intersections, axis=0)

    def normalize_table_grid(
        self, grid_points: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Normalizes the grid determined by intersections of lines.
        It aligns points vertically and horizontally
        if they are almost on the same x and y axis,
        and merges the points that are close together.

        Args:
            grid_points (npt.NDArray): the (x, y) coordinates of points defining the table grid,
                i.e intersections point of lines. As an array of shape (n_points, 2).

        Returns:
            npt.NDArray[np.float32] : the aligned points.
        """
        x = grid_points[:, 0]
        groups_by_x = self._get_grouped_idxes(x)
        for group in groups_by_x:
            grid_points[group, 0] = np.mean(grid_points[group, 0])

        y = grid_points[:, 1]
        groups_by_y = self._get_grouped_idxes(y)
        for group in groups_by_y:
            grid_points[group, 1] = np.mean(grid_points[group, 1])

        return np.unique(grid_points, axis=0)

    def _get_grouped_idxes(self, values: list[float]) -> list[npt.NDArray[np.float32]]:
        """Considering a list of values, groups the values together if
        they are closer than the specified threshold, and returns the indices
        of the groups.
        For examples, if values = [2, 3, 5, 10] and threshold = 2,
        it will return [[0,1], [2], [3]]"""
        x = np.sort(values)
        diff = x[1:] - x[:-1]
        gps = np.concatenate([[0], np.cumsum(diff >= self.line_width_threshold)])

        return [np.argsort(values)[gps == i] for i in range(gps[-1] + 1)]

    def _normalize_lines_grid(
        self,
        line_coords: npt.NDArray[np.float32],
        intersections: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """Remaps the points of all the detected lines on the detected intersections.

        Args:
            line_coords (npt.NDArray[np.float32]): the coordinates of the detected lines,
                as an array of shape (n_lines, 4)
            intersections (npt.NDArray[np.float32]) : the coordinates of the intersections,
                as an array of shape (n_intersections, 2)

        Returns:
            npt.NDArray[np.float32]: _description_
        """
        sorted_x_y = np.sort(intersections, axis=0)
        x_targets = np.unique(sorted_x_y[:, 0])
        y_targets = np.unique(sorted_x_y[:, 1])

        x_bins = (x_targets[1:] + x_targets[:-1]) / 2
        y_bins = (y_targets[1:] + y_targets[:-1]) / 2

        lines_as_points = line_coords.reshape(-1, 2)
        normalized_x = x_targets[np.digitize(lines_as_points[:, 0], x_bins)]
        normalized_y = y_targets[np.digitize(lines_as_points[:, 1], y_bins)]
        points_as_lines = np.stack([normalized_x, normalized_y], axis=-1).reshape(-1, 4)
        # reorder xs and ys so that (x0, y0) is topleft and (x1, y1) is bottomright
        points_as_lines = np.column_stack(TableFinder._bounding_boxes(points_as_lines))

        return points_as_lines

    @staticmethod
    def _bounding_boxes(
        coordinates: npt.NDArray[np.float32],
    ) -> tuple[
        npt.NDArray[np.float32],
        npt.NDArray[np.float32],
        npt.NDArray[np.float32],
        npt.NDArray[np.float32],
    ]:
        """Calculate bounding boxes for line segments."""
        x1 = np.minimum(coordinates[:, 0], coordinates[:, 2])
        y1 = np.minimum(coordinates[:, 1], coordinates[:, 3])
        x2 = np.maximum(coordinates[:, 0], coordinates[:, 2])
        y2 = np.maximum(coordinates[:, 1], coordinates[:, 3])

        return x1, y1, x2, y2

    def _bboxes_intersect_or_nearly(
        self,
        bbox_a: tuple[float],
        bbox_b: tuple[float],
    ) -> bool:
        """Check if two bounding boxes of lines a and b intersect or are nearly intersecting.
        Arguments must be bbox coordinates as a tuple representing (x1, y1, x2, y2)."""
        x1a, y1a, x2a, y2a = bbox_a
        x1b, y1b, x2b, y2b = bbox_b
        return (
            (x1a <= x2b + self.snap_tolerance)
            & (x2a + self.snap_tolerance >= x1b)
            & (y1a <= y2b + self.snap_tolerance)
            & (y2a + self.snap_tolerance >= y1b)
        )

    def _build_adjacency_matrix(
        self, coordinates: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.bool_]:
        """Builds the adjencency matrix, i.e matrix denoting which
        lines intersect with one another.

        Args:
            coordinates (npt.NDArray[np.float32]): a 2D array of shape (n_lines, 4) representing line coordinates.

        Returns:
            npt.NDArray[np.bool_]: A 2D matrix of shape (n_lines, n_lines) representing which
                line intersects with other lines.
        """
        x1, y1, x2, y2 = TableFinder._bounding_boxes(coordinates)

        n = len(coordinates)
        adjacency_matrix = np.zeros((n, n), dtype=bool)
        for i in range(n):
            for j in range(i + 1, n):
                if self._bboxes_intersect_or_nearly(
                    (x1[i], y1[i], x2[i], y2[i]), (x1[j], y1[j], x2[j], y2[j])
                ):
                    adjacency_matrix[i, j] = True
                    adjacency_matrix[j, i] = True

        return adjacency_matrix

    @staticmethod
    def _connected_components(
        adjacency_matrix: npt.NDArray[np.bool_],
    ) -> list[list[int]]:
        """
        Find connected components in the graph represented by the adjacency matrix.
        In other words, groups the lines that belong to the same table on the page.

        Args:
            adjacency_matrix: the matrix representing which line intersects which line.
                (output of build_adjacency_matrix()).

        Returns:
            list[list[int]]: a list of list of indexes representing grouped lines
        """
        n = len(adjacency_matrix)
        visited = np.zeros(n, dtype=bool)
        components: list[list[int]] = []

        for start in range(n):
            if not visited[start]:
                stack = [start]
                component: list[int] = []
                while stack:
                    node = stack.pop()
                    if not visited[node]:
                        visited[node] = True
                        component.append(node)
                        neighbors = np.where(adjacency_matrix[node])[0]
                        stack.extend(neighbors)
                components.append(component)

        return components

    def group_lines_by_table(
        self, coordinates: npt.NDArray[np.float32]
    ) -> list[npt.NDArray[np.float32]]:
        """Considering a list of matrix coordinates of shape (n_lines, 4),
        with each row reprensenting (x1, y1, x2, y2) coordinates of the lines,
        groups the lines together if they belong to the same table.

        Args:
            coordinates (npt.NDArray[np.float32]): the coordinates of lines.

        Returns:
            list[npt.NDArray[np.float32]]: the groups of lines coordinates, grouped by table.
        """
        adjacency_matrix = self._build_adjacency_matrix(coordinates)
        indexes_of_groups = TableFinder._connected_components(adjacency_matrix)
        return [coordinates[group] for group in indexes_of_groups if group]

    @staticmethod
    def _get_cells(
        intersections: npt.NDArray[np.float32],
        lines_coordinates: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """Considering a list of intersection points in a table,
        and a list of detected lines, gets all the cells of table.

        Args:
            intersections (npt.NDArray[np.float32]): a list of intersection points,
                as an array of shape (n_points, 2) of (x,y) coordinates.
            lines_coordinates (npt.NDArray[np.float32]): an array of shape (n_lines, 4)
                where each row contains coordinates of the x0, y0, x1, y1 of each line.

        Returns:
            npt.NDArray[np.float32]: the list of cells, as an array of shape
                (n_cells, 4) where each row is (x0, y0, x1, y1) coordinates.
        """
        cells_coords = TableFinder.get_table_cells_without_merged_cells(intersections)
        valid_cell_borders_mask = TableFinder._get_cell_borders_validity(
            cells_coords, lines_coordinates
        )
        if valid_cell_borders_mask.all():  # No merged cells
            return cells_coords
        # Remove invalid cells
        valid_cells_mask = valid_cell_borders_mask.all(axis=1)
        valid_cells = cells_coords[valid_cells_mask]
        # For invalid cells, find the merged cells
        topleft_corners_of_merged_cells = cells_coords[~valid_cells_mask][:, :2]
        line_combinations_coords = TableFinder._get_recombined_lines(lines_coordinates)
        merged_cells = [
            TableFinder._get_merged_cell(point, intersections, line_combinations_coords)
            for point in topleft_corners_of_merged_cells
        ]
        merged_cells = np.unique(np.vstack(merged_cells), axis=0)

        return np.unique(np.vstack((merged_cells, valid_cells)), axis=0)

    @staticmethod
    def get_table_cells_without_merged_cells(
        intersections: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """From line intersections, build cells as if
        no cells where merged.

        Args:
            intersections (npt.NDArray[np.float32]): a list of intersection points,
                as an array of shape (n_points, 2) of (x,y) coordinates.

        Returns:
            npt.NDArray[np.float32]: the list of cells, as an array of shape
                (n_cells, 4) where each row is (x0, y0, x1, y1) coordinates.
        """
        # Get unique x and y positions from intersections
        xs, ys = np.unique(intersections[:, 0]), np.unique(intersections[:, 1])
        # Generate cells
        x1, x2 = np.repeat(xs[:-1], len(ys) - 1), np.repeat(xs[1:], len(ys) - 1)
        y1, y2 = np.tile(ys[:-1], len(xs) - 1), np.tile(ys[1:], len(xs) - 1)
        cells = np.column_stack([x1, y1, x2, y2])

        return cells

    @staticmethod
    def _get_merged_cell(
        topleft_point: npt.NDArray[np.float32],
        intersections: npt.NDArray[np.float32],
        lines_combinations: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """Considering a point coordinate that would be topleft corner of a cell,
        and a list of intersections points, and a list of lines,
        get its cells coordinates corresponding to the point.

        Args:
            topleft_point (npt.NDArray[np.float32]): an array of size (1, 2) reprensenting
                the (x, y) coordinates of what is supposedly the topleft corner of a cell.
            intersections (npt.NDArray[np.float32]): a list of intersection points,
                as an array of shape (n_points, 2) of (x,y) coordinates.
            lines_combinations: npt.NDArray[np.float32]: an array representing
                all the combinations of lines that can be made for the detected lines.

        Returns:
            npt.NDArray[np.float32] : An array of shape (0, 4) or (1, 4) representing the cell coordinates
                corresponding to provided points.
        """
        cells = TableFinder._get_potential_cells_for_point(topleft_point, intersections)
        if cells.size:
            cells = TableFinder._remove_cells_with_invalid_borders(
                cells, lines_combinations
            )
            cells = TableFinder._remove_nesting_cells(cells)
            assert cells.shape[0] in [
                0,
                1,
            ], "Error, only 1 or 0 cells should be returned."
        else:
            cells = np.empty((0, 4), dtype=np.float32)

        return cells

    @staticmethod
    def _get_potential_cells_for_point(
        point: npt.NDArray[np.float32], intersections: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Considering a point and a list of intersection points,
        gets all the possible cells that can be made for that point.

        Example:
        o11---o12---o13
         |    |     |
        o21---o22---o23
         |    |     |
        o31---o32---o33

        Considering the above table, for point o11,
        the potention cells would be delimited by
        [o11, o22], [o11, o23], [o11, o32], [o11, o33]

        Args:
            point (npt.NDArray[np.float32]): point coordinates (array of shape (1, 2))
            intersections (npt.NDArray[np.float32]): a list of intersection points,
                as an array of shape (n_points, 2) of (x,y) coordinates.

        Returns:
            npt.NDArray[np.float32]: the list of potential cell, as an array of shape
                (n_cells, 4) where each row is (x0, y0, x1, y1) coordinates.
        """
        potential_points = intersections[
            (intersections[:, 0] > point[0]) & (intersections[:, 1] > point[1])
        ]
        return np.concatenate(
            [np.broadcast_to(point, (potential_points.shape[0], 2)), potential_points],
            axis=1,
        )

    @staticmethod
    def _remove_cells_with_invalid_borders(
        cells_coords: npt.NDArray[np.float32],
        lines_coordinates: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """Considering a list of cells, and a list of detected lines,
        remove the cells for which the borders are not along a line.
        In other words, verifies that all borders of each cell are actually along a detected line.

        Args:
            cells_coords (npt.NDArray[np.float32]): an array of shape (n_cells, 4) where each row contains
                the (x1, y1, x2, y2) coordinates of the cells.
            lines_coordinates (npt.NDArray[np.float32]): an array of shape (n_lines, 4) where each row contains
                coordinates of the x0, y0, x1, y1 of each line.
        """
        valid_cell_borders_mask = TableFinder._get_cell_borders_validity(
            cells_coords, lines_coordinates
        )
        valid_cells = cells_coords[valid_cell_borders_mask.all(axis=1)]

        return valid_cells

    @staticmethod
    def _get_cell_borders_validity(
        cells_coords: npt.NDArray[np.float32],
        lines_coordinates: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.bool_]:
        """Considering a list of cells, and a list of detected lines,
        returns an array of shape (n_cells, 4) where each row represents
        whether or not each border of cells exists in lines_coordinates.
        Each row represents the validity of left, top, right, and bottom border in that order.

        Args:
            cells_coords (npt.NDArray[np.float32]): an array of shape (n_cells, 4) where each row contains
                the (x1, y1, x2, y2) coordinates of the cells.
            lines_coordinates (npt.NDArray[np.float32]): an array of shape (n_lines, 4) where each row contains
                coordinates of the x0, y0, x1, y1 of each line.
        """
        x0, y0, x1, y1 = TableFinder._bounding_boxes(cells_coords)
        # build array of shape (n_cells, 4, 4), in which we have the coords of the 4 borders of each cell.
        left_lines = np.array([x0, y0, x0, y1]).T
        top_lines = np.array([x0, y0, x1, y0]).T
        right_lines = np.array([x1, y0, x1, y1]).T
        bottom_lines = np.array([x0, y1, x1, y1]).T

        cells_borders = np.stack(
            [left_lines, top_lines, right_lines, bottom_lines], axis=1
        )
        lines_coordinates_set = set(map(tuple, lines_coordinates))
        valid_borders_mask = np.array(
            [
                [tuple(border) in lines_coordinates_set for border in cell_borders]
                for cell_borders in cells_borders
            ],
            np.bool_,
        )

        return valid_borders_mask

    @staticmethod
    def _remove_nesting_cells(
        cells_coords: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """Considering a list of cells, one keep the cells that do not contain
        any other cells.

        Args:
            cells_coords (npt.NDArray[np.float32]): an array of shape (n_cells, 4) where each row contains
                the (x1, y1, x2, y2) coordinates of the cells.

        Returns:
            npt.NDArray[np.float32]: cells coordinates of cells that do not contain any other cell.
        """
        x0, y0, x1, y1 = TableFinder._bounding_boxes(cells_coords)
        # Compare each coord of each box with other boxes
        x0_mask = x0[:, np.newaxis] <= x0
        y0_mask = y0[:, np.newaxis] <= y0
        x1_mask = x1[:, np.newaxis] >= x1
        y1_mask = y1[:, np.newaxis] >= y1
        containment_mask = x0_mask & y0_mask & x1_mask & y1_mask
        # Ignore self-containment by setting diagonal to False
        np.fill_diagonal(containment_mask, False)
        # Find cells that do NOT contain any other cell
        containment_mask = ~np.any(containment_mask, axis=1)

        return cells_coords[containment_mask]

    @staticmethod
    def point_is_on_line(
        point: tuple[float, float],
        line: tuple[float, float, float, float],
        tolerance: float = 1e-6,
    ) -> bool:
        """Check if a point is on a line segment."""
        x1, y1, x2, y2 = line
        x, y = point
        # Check if the point lies on the line using vector cross product
        if abs((y - y1) * (x2 - x1) - (x - x1) * (y2 - y1)) > tolerance:
            return False
        # Check if the point is within the line segment bounds
        if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return True

        return False

    @staticmethod
    def subdivide_lines(
        lines: npt.NDArray[np.float32], intersections: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Subdivides all the lines that cross an intersection point.

        Exemple : o1---o2---o3---o4. Considering we have line (o1-o4),
        this method could return lines [(o1-o2),(o2-o3),(o3-o4)]

        Args:
            lines_coordinates (npt.NDArray[np.float32]): an array of shape (n_lines, 4) where each row contains
                coordinates of the x0, y0, x1, y1 of each line.
            intersections (npt.NDArray[np.float32]): a list of intersection points,
                as an array of shape (n_points, 2) of (x,y) coordinates.

        Returns:
            npt.NDArray[np.float32]: the cooridiantes of subdivided lines.
        """
        new_lines: list[tuple[float, float, float, float]] = []

        for line in lines:
            split_points: list[tuple[float, float]] = []

            # Check each intersection to see if it lies on the line
            for intersection in intersections:
                if TableFinder.point_is_on_line(intersection, line):
                    split_points.append(intersection)
            # Sort the split points in the order they appear on the line
            x0, y0 = line[:2]
            split_points.sort(
                key=lambda p, x0=x0, y0=y0: abs(p[0] - x0) + abs(p[1] - y0)
            )
            # Subdivide the line at each of these split points
            x1, y1 = line[:2]
            for x, y in split_points:
                new_lines.append([x1, y1, x, y])
                x1, y1 = x, y
            new_lines.append([x1, y1, line[2], line[3]])
        # Get uniues lines and remove lines that are actually points
        new_lines = np.unique(np.array(new_lines), axis=0)
        return new_lines[
            (new_lines[:, 0] != new_lines[:, 2]) | (new_lines[:, 1] != new_lines[:, 3])
        ]

    @staticmethod
    def _get_recombined_lines(
        lines_coordinates: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """Gets the coordinates of all te lines that can be built
        based on recombination of continuous segments along x and y axis.

        Exemple:
        o11---o12---o13---o14
        Considering the above segments, this method would return
        all segments provided as arg + the coordinates of [o1, o3], [o1, o4], [o2, o4]
        Note: works for both horizontal and vertical axes.

        Args:
            lines_coordinates (npt.NDArray[np.float32]): A numpy array of horizontal and vertical segments
                of shape (n_lines, 4) where each row is [x0, y0, x1, y1] coordinates of a line.

        Returns:
            npt.NDArray[np.float32]: An array of shape (n, 4) containing
            all the coordinates of the segments + every possible recombination.
        """
        combined_lines = lines_coordinates
        n_prev_combined_lines = -1

        while len(combined_lines) != n_prev_combined_lines:
            n_prev_combined_lines = len(combined_lines)
            new_combinations: list[list[float]] = []
            # Build dictionaries for quick lookup of start and end points
            start_to_indices: dict[tuple[float, float], list[int]] = {}
            for idx, line in enumerate(combined_lines):
                start_point = (line[0], line[1])
                start_to_indices.setdefault(start_point, []).append(idx)

            for idx, (x0, y0, x1, y1) in enumerate(combined_lines):
                # Look for lines that start where the current line ends
                end_point = (x1, y1)
                if end_point in start_to_indices:
                    # Combine with all lines starting at the end point
                    for next_idx in start_to_indices[end_point]:
                        # only pay attention to vertical/horizontal lines
                        if (
                            combined_lines[next_idx][2] == x0
                            or combined_lines[next_idx][3] == y1
                        ):
                            new_line = [
                                x0,
                                y0,
                                combined_lines[next_idx][2],
                                combined_lines[next_idx][3],
                            ]
                            new_combinations.append(new_line)

            if new_combinations:
                # Add new combinations and remove duplicates
                combined_lines = np.unique(
                    np.vstack(
                        (combined_lines, np.array(new_combinations, dtype=np.float32))
                    ),
                    axis=0,
                )

        return combined_lines

    @staticmethod  # TODO : investigate if possible to replace _get_recombined_lines with this one
    def _get_recombined_lines_v2(
        lines_coordinates: npt.NDArray[np.float32],
    ) -> npt.NDArray[np.float32]:
        """WARNING : IMPLEMENTATION DOESN'T WORK
        I leave it here for further investigation as it might be faster and easier to read
        than current used implementation : _get_recombined_lines.
        """
        prev_n_lines = -1  # dummy to go in while loop
        while prev_n_lines < lines_coordinates.shape[0]:
            prev_n_lines = lines_coordinates.shape[0]
            start_points = lines_coordinates[:, :2]
            end_points = lines_coordinates[:, 2:]
            # Get mask where start point and endpoints match
            mask = (start_points[:, np.newaxis, :] == end_points[np.newaxis, :, :]).all(
                axis=2
            )  # PROBLEM WITH THIS LINE
            new_lines = np.hstack(
                [start_points[mask.any(axis=0)], end_points[mask.any(axis=1)]]
            )
            new_lines = new_lines[
                (new_lines[:, 0] == new_lines[:, 2])
                | (new_lines[:, 1] == new_lines[:, 3])
            ]  # only vertical and horizontal lines
            lines_coordinates = np.unique(
                np.vstack([new_lines, lines_coordinates]), axis=0
            )

        return lines_coordinates

    @staticmethod
    def _table_sanity_check(cells_coords: npt.NDArray[np.float32]) -> bool:
        """Perfoms a sanity check of the parsed table.
        Checks that the area of the table is equal to the sum of the area of its cells.

        Args:
            cells (npt.NDArray[np.float32]): the cells of the table detected.
                Array of shape (n_cells, 4) where each row is x0, y0, x1, y1 coordinates of the cell.

        Returns:
            bool: returns True if the sanity check is passed, and False if the table
                is likely to be a false detection.
        """
        x0, y0, x1, y1 = (
            cells_coords[:, 0],
            cells_coords[:, 1],
            cells_coords[:, 2],
            cells_coords[:, 3],
        )

        table_area = (np.max(x1) - np.min(x0)) * (np.max(y1) - np.min(y0))
        cells_areas = np.abs((x1 - x0) * (y1 - y0))
        total_cells_area = np.sum(cells_areas)

        return np.isclose(table_area, total_cells_area, rtol=0.02)
