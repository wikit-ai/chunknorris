import re

import pymupdf  # type: ignore -> no stubs

from chunknorris.parsers import PdfParser
from chunknorris.core.components import MarkdownDoc


def test_parse_file(pdf_parser: PdfParser, pdf_filepath: str):
    parser_output = pdf_parser.parse_file(pdf_filepath)
    assert isinstance(parser_output, MarkdownDoc)
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


def test_parse_tables(pdf_parser: PdfParser, pdf_tables_filepath: str):
    _ = pdf_parser.parse_file(pdf_tables_filepath)
    assert len(pdf_parser.tables) == 1
    # Check tables 0 is valid
    assert len(pdf_parser.tables[0].cells) == 18
    assert pdf_parser.tables[0].to_pandas().shape == (4, 5)
    table_0_as_md = pdf_parser.tables[0].to_markdown()
    assert len(re.findall("Col2", table_0_as_md)) == 4
    assert len(re.findall("Col3 Col4", table_0_as_md)) == 4
    assert len(re.findall("Col5", table_0_as_md)) == 4


def test_parse_string(pdf_parser: PdfParser, pdf_filepath: str):
    byte_string = pymupdf.open(pdf_filepath).tobytes()  # type: ignore -> missing typing : pymupdf.open() -> pymupdf.Document
    md_string = pdf_parser.parse_string(byte_string)
    assert isinstance(md_string, MarkdownDoc)
