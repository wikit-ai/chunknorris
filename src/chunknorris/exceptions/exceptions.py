class ChunkNorrisException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class PdfParserException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class OCRException(PdfParserException):
    """Raised when an OCR engine is misconfigured or fails.
    Subclasses PdfParserException for backward compatibility."""


class ImageParserException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class TextNotFoundException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class PageNotFoundException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
