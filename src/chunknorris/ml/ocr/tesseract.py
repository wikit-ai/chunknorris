import os

import pymupdf  # type: ignore : no stubs

from ...exceptions.exceptions import PdfParserException
from .base import PageOCREngine


class TesseractOCR(PageOCREngine):
    """OCR engine using Tesseract through pymupdf's integrated OCR support.
    Requires Tesseract to be installed and the "TESSDATA_PREFIX"
    environment variable to point to the traineddata files.
    """

    def __init__(self, language: str = "fra+eng", dpi: int = 72) -> None:
        """Initializes the Tesseract OCR engine.

        Args:
            language (str, optional): the languages to consider for OCR.
                Must be a string of 3 letter codes languages separated by "+".
                Example : "fra+eng+ita". Defaults to "fra+eng".
            dpi (int, optional): the resolution used to render the pages before OCR.
                Defaults to 72.
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
            raise PdfParserException(
                'To use OCR, the "TESSDATA_PREFIX" must be set as environment variable in order to locate traineddata files. For more info see https://pymupdf.readthedocs.io/en/latest/installation.html#enabling-integrated-ocr-support\nYou may otherwise want to deactivate OCR : PdfParser(use_ocr="never").',
            )
        for lang in self.language.split("+"):
            if not os.path.exists(
                os.path.join(tessdata_location, f"{lang}.traineddata")
            ):
                raise PdfParserException(
                    f"Tesseract's {lang}.traineddata file not found at {tessdata_location}. You might need to download the corresponding file from https://github.com/tesseract-ocr/tessdata and place it in {tessdata_location}",
                )

    def get_textpage(self, page: pymupdf.Page) -> pymupdf.TextPage:
        return page.get_textpage_ocr(  # type: ignore : missing typing in pymupdf
            language=self.language, dpi=self.dpi, full=False
        )
