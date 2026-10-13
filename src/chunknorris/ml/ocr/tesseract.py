import os

import pymupdf  # type: ignore : no stubs

from ...exceptions.exceptions import OCRException
from .base import PageOCREngine


class TesseractOCR(PageOCREngine):
    """OCR engine using Tesseract through pymupdf's integrated OCR support.
    Requires Tesseract to be installed and the "TESSDATA_PREFIX"
    environment variable to point to the traineddata files.
    """

    # Bounds (dpi) of the resolution used with dpi=None. Tesseract reads best
    # around 300 dpi, higher resolutions only slow it down
    _MIN_DPI: int = 72
    _MAX_DPI: int = 300

    def __init__(self, language: str = "fra+eng", dpi: int | None = 72) -> None:
        """Initializes the Tesseract OCR engine.

        Args:
            language (str, optional): the languages to consider for OCR.
                Must be a string of 3 letter codes languages separated by "+".
                Example : "fra+eng+ita". Defaults to "fra+eng".
            dpi (int | None, optional): the resolution used to render the pages before OCR.
                If None, the pages are rendered at the native resolution of their images,
                between 72 and 300 dpi: slower, but better suited to scans. Defaults to 72.
        """
        self.language = language
        self.dpi = dpi

    @property
    def name(self) -> str:
        return "tesseract"

    def __repr__(self) -> str:
        return f"TesseractOCR(language={self.language!r}, dpi={self.dpi})"

    def validate(self) -> None:
        tessdata_location = os.environ.get("TESSDATA_PREFIX")
        if not tessdata_location:
            raise OCRException(
                'To use OCR, the "TESSDATA_PREFIX" must be set as environment variable in order to locate traineddata files. For more info see https://pymupdf.readthedocs.io/en/latest/installation.html#enabling-integrated-ocr-support\nYou may otherwise want to deactivate OCR : PdfParser(use_ocr="never").',
            )
        for lang in self.language.split("+"):
            if not os.path.exists(
                os.path.join(tessdata_location, f"{lang}.traineddata")
            ):
                raise OCRException(
                    f"Tesseract's {lang}.traineddata file not found at {tessdata_location}. You might need to download the corresponding file from https://github.com/tesseract-ocr/tessdata and place it in {tessdata_location}",
                )

    def get_textpage(self, page: pymupdf.Page) -> pymupdf.TextPage:
        dpi = self.dpi if self.dpi is not None else TesseractOCR._get_native_dpi(page)
        return page.get_textpage_ocr(  # type: ignore : missing typing in pymupdf
            language=self.language, dpi=dpi, full=False
        )

    @staticmethod
    def _get_native_dpi(page: pymupdf.Page) -> int:
        """Gets the resolution at which the page must be rendered for its images
        to keep their native resolution, between _MIN_DPI and _MAX_DPI.

        Args:
            page (pymupdf.Page): the page.

        Returns:
            int: the resolution, in dpi.
        """
        native_dpi = max(
            (
                72 * image["width"] / pymupdf.Rect(image["bbox"]).width
                for image in page.get_image_info()  # type: ignore : missing typing in pymupdf
                if pymupdf.Rect(image["bbox"]).width > 0
            ),
            default=TesseractOCR._MIN_DPI,
        )
        return round(min(max(native_dpi, TesseractOCR._MIN_DPI), TesseractOCR._MAX_DPI))
