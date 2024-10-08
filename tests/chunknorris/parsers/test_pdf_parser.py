import re
import pymupdf
from chunknorris.parsers import PdfParser
from chunknorris.types import MarkdownString


def test_parse_file(pdf_parser: PdfParser, pdf_filepath: str):
    md_string = pdf_parser.parse_file(pdf_filepath)
    assert isinstance(md_string, MarkdownString)
    # Assert header and footers have been detected
    assert len([span for span in pdf_parser.spans if span.is_header_footer]) > 0
    ### Table parsing ###
    # Assert the table has been detected and no false detection
    assert len(pdf_parser.tables) == 1
    # Assert teble cells have been parsed correctly
    assert len(pdf_parser.tables[0].cells) == 18
    # Assert the merged cell are unpacked on multiple cells when converting to markdown
    assert len(re.findall("No", pdf_parser.tables[0].to_markdown())) == 5
    ### Table of content detection ###
    # Assert table of content has been found
    assert len(pdf_parser.toc) == 10
    # Assert correct level have been found
    assert (
        len([title for title in pdf_parser.toc if title.level == 2]) == 2
        and len([title for title in pdf_parser.toc if title.level == 1]) == 8
    )
    ### Main Title ###
    assert pdf_parser.main_title == "DUMMY  DOCUMENT  TITLE  Dummy subtitle"


def test_parse_string(pdf_parser: PdfParser, pdf_filepath: str):
    byte_string = pymupdf.open(pdf_filepath).tobytes()
    md_string = pdf_parser.parse_string(byte_string)
    assert isinstance(md_string, MarkdownString)
