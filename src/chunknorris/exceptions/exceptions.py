class ChunkNorrisException(Exception):
    def __init__(self, message: str):
        pass


class PdfParserException(Exception):
    def __init__(self, message: str):
        pass


class TextNotFoundException(Exception):
    def __init__(self, message: str):
        pass


class PageNotFoundException(Exception):
    def __init__(self, message: str):
        pass
