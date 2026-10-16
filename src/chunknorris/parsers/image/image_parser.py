from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

import pymupdf  # type: ignore : no stubs

from ...core.components import MarkdownDoc
from ...exceptions.exceptions import ImageParserException
from ...ml.ocr import OCREngine, TesseractOCR
from ..pdf.pdf_parser import PdfParser
from ..pdf.tools import TableFinder

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


class ImageParser(PdfParser):
    """Parses images (png, jpg, tiff...) by running OCR on them.
    The image is converted to a pdf, one page per frame, that goes
    through the PdfParser with OCR always on. A DocumentOCREngine
    such as MistralOCR receives the frames as images, one request per frame.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
        {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}
    )
    _PAGES_ARE_IMAGES: bool = True

    def __init__(
        self,
        *,
        ocr_engine: OCREngine | None = None,
        extract_tables: bool = True,
        table_finder: TableFinder = TableFinder(),
        add_headers: bool = True,
        body_line_spacing: float | None = None,
        detect_orientation: bool = False,
    ) -> None:
        """Initializes an image parser.

        Args:
            ocr_engine (OCREngine | None, optional): the OCR engine to use.
                MistralOCR(image_captioning=True) is recommended: it provides the layout
                of the image and captions its pictures. If None, defaults to TesseractOCR(dpi=None),
                that reads the image at its native resolution.
            extract_tables (bool, optional): whether or not tables should be extracted.
                Only used with a PageOCREngine such as TesseractOCR. Defaults to True.
            table_finder (TableFinder, optional): the table finder to use for parsing the tables.
                Only used with a PageOCREngine such as TesseractOCR.
            add_headers (bool, optional): if True, the parser will try to style the headers.
                Only used with a PageOCREngine such as TesseractOCR. Defaults to True.
            body_line_spacing (float, optional): the size of the space between 2 lines of the body.
                Only used with a PageOCREngine such as TesseractOCR. If None, found automatically.
            detect_orientation (bool, optional): if True, the frames are turned upright before OCR,
                according to an ML orientation classifier loaded on startup.
                Requires ``onnxruntime`` or ``openvino`` and ``huggingface-hub``. Defaults to False.
        """
        super().__init__(
            extract_tables=extract_tables,
            table_finder=table_finder,
            add_headers=add_headers,
            use_ocr="always",
            ocr_engine=ocr_engine or TesseractOCR(dpi=None),
            body_line_spacing=body_line_spacing,
            detect_orientation=detect_orientation,
        )

    def parse_image(
        self, image: PILImage, page_start: int = 0, page_end: int | None = None
    ) -> MarkdownDoc:
        """Parses a PIL image and returns the parsed MarkdownDoc object.
        All the frames of a multi-frame image (tiff, gif...) are parsed.

        Args:
            image (PIL.Image.Image): the image to parse.
            page_start (int, optional): the frame to start parsing from. Defaults to 0.
            page_end (int, optional): the frame to stop parsing. None to parse until last frame. Defaults to None.

        Returns:
            MarkdownDoc: The MarkdownDoc to be passed to MarkdownChunker.
        """
        # tiff keeps every frame and supports all image modes (RGBA, CMYK, P...)
        buffer = io.BytesIO()
        image.save(buffer, format="TIFF", save_all=True, compression="tiff_deflate")
        return self.parse_string(buffer.getvalue(), page_start, page_end)

    def read_file(self, filepath_or_stream: str | bytes) -> None:
        """Opens an image and converts it to a pdf document.

        Args:
            filepath_or_stream (str | bytes): Filepath to an image, or byte stream.
        """
        self.cleanup_memory()

        try:
            if isinstance(filepath_or_stream, str):
                self.filepath = filepath_or_stream
                if (
                    Path(filepath_or_stream).suffix.lower()
                    not in self.SUPPORTED_EXTENSIONS
                ):
                    raise ImageParserException(
                        f"Only {sorted(self.SUPPORTED_EXTENSIONS)} files can be passed to ImageParser."
                    )
                image = pymupdf.open(filepath_or_stream)
            else:
                image = pymupdf.open(stream=filepath_or_stream)
        except pymupdf.FileDataError as e:
            raise ImageParserException(f"Unable to open the image: {e}") from e
        # pymupdf also opens pdfs and text documents (html, epub, txt...)
        if image.is_pdf or image.is_reflowable:  # type: ignore : missing typing in pymupdf
            document_format: str = image.metadata["format"]  # type: ignore : missing typing in pymupdf -> document.metadata : dict[str, str]
            image.close()
            raise ImageParserException(
                f"Only images can be passed to ImageParser, got a {document_format!r} document."
            )
        self.document = pymupdf.open("pdf", image.convert_to_pdf())  # type: ignore : missing typing in pymupdf
        image.close()
