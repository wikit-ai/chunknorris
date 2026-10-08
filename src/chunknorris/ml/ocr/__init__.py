"""OCR engines that can be plugged into the PdfParser.

Usage::

    from chunknorris.ml.ocr import MistralOCR
    from chunknorris.parsers import PdfParser

    parser = PdfParser(ocr_engine=MistralOCR(image_captioning=True))
"""

from .base import DocumentOCREngine, OCREngine, PageOCREngine
from .mistral import MistralOCR
from .tesseract import TesseractOCR
from .types import OCRBlock, OCRDocument, OCRImage

__all__ = [
    "DocumentOCREngine",
    "MistralOCR",
    "OCRBlock",
    "OCRDocument",
    "OCREngine",
    "OCRImage",
    "PageOCREngine",
    "TesseractOCR",
]
