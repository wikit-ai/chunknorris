from collections import Counter
from typing import Literal

import pymupdf  # type: ignore : no stubs

from ....exceptions.exceptions import PdfParserException
from .components import TextBlock, TextLine, TextSpan
from .components_tables import PdfTable, TableFinder


class PdfParserState:
    """Contains the state of the class.
    Intended to be inherited by all pdfParser components
    """

    _document: pymupdf.Document | None = None
    filepath: str | None = None
    page_start: int = 0
    page_end: int | None = None
    spans: list[TextSpan] = []
    lines: list[TextLine] = []
    blocks: list[TextBlock] = []
    tables: list[PdfTable] = []
    table_finder: TableFinder = TableFinder()
    main_title: str = ""
    main_body_fontsizes: list[float] = []
    document_fontsizes: list[float] = []
    main_body_is_bold: bool = False
    document_orientation: Literal["portrait", "landscape"]

    @property
    def document(self) -> pymupdf.Document:
        if self._document is None:
            raise PdfParserException(
                "No document parsed. You might call parser.parse_file('my_file.pdf')."
            )
        return self._document

    @document.setter
    def document(self, doc: pymupdf.Document) -> None:
        self._document = doc


class DocSpecsExtraction(PdfParserState):

    def _set_document_specifications(self) -> None:
        """Set the specifications of various specifications of the document.
        Stores the attributes in :
        - self.document_orientation -> the orientation of the document (portrait or landscape)
        - self.main_body_fontsizes -> the fontsizes used for the body content of the document
        - self.document_fonsizes -> a sorted list of fontsizes in the document (bigger than body)
        - self.main_body_is_bold -> whether or not the main body is written in bold

        Meant to be called after the creation of the TextBlock objects.
        """
        self._set_document_font_specs()
        self._set_document_orientation()

    def _set_document_orientation(self) -> None:
        """Determines the orientation of the document
        using the first page of the document.

        - self.document_orientation -> the orientation of the document (portrait or landscape)
        """
        page_rect: pymupdf.Rect = self.document[0].rect
        self.document_orientation = "portrait" if page_rect.height > page_rect.width else "landscape"  # type: ignore missing typing in pymupdf | Rect.height : float, Rect.width : float

    def _set_document_font_specs(self):
        """Set the specifications of various specifications
        regarding the fonts in the document.
        Stores the attributes in :
        - self.main_body_fontsizes -> the fontsizes used for the body content of the document
        - self.document_fonsizes -> a sorted list of fontsizes in the document (bigger than body)
        - self.main_body_is_bold -> whether or not the main body is written in bold
        """
        fontsize_counts = Counter(
            line.fontsize
            for line in self.lines
            if not line.is_empty and line.orientation == (1.0, 0.0)
        )
        if not fontsize_counts:
            return
        self.document_fontsizes = list(fontsize_counts.keys())
        self.main_body_fontsizes = [
            fontsize
            for fontsize, occurence in fontsize_counts.items()
            if occurence > len(self.lines) * 0.1
        ]
        if not self.main_body_fontsizes:
            return
        # determine whether or not the body of document is written in bold (if 30% of the lines are bold, we consider the main body is bold)
        bold_main_body_lines = [
            line.is_bold
            for line in self.lines
            if line.fontsize in self.main_body_fontsizes and not line.is_empty
        ]
        self.main_body_is_bold = (
            sum(bold_main_body_lines) / len(bold_main_body_lines) > 0.3
        )
