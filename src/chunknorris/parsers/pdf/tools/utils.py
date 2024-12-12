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


class PdfParserUtilities(PdfParserState):

    def get_document_orientation(self) -> Literal["portrait", "landscape"]:
        """Determines the orientation of the document
        using the first page of the document.

        Returns:
            str: the orientation "landscape" or "portrait"
        """
        page_dims: pymupdf.Rect = self.document[0].rect

        return "portrait" if page_dims.height > page_dims.width else "landscape"  # type: ignore missing typing in pymupdf | Rect.height : float, Rect.width : float
