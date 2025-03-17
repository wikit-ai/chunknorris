import re

from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import DocxParser


def test_parse_file(docx_parser: DocxParser, docx_filepath: str):
    parser_output = docx_parser.parse_file(docx_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    ### Table parsing ###
    # Assert the merged cell are unpacked on multiple cells when converting to markdown
    assert len(re.findall(r"\bNo\b", parser_output.to_string())) == 5


def test_parse_tables(docx_parser: DocxParser, docx_tables_filepath: str):
    parser_output = docx_parser.parse_file(docx_tables_filepath)
    ### Table parsing ###
    # Assert the merged cell are unpacked on multiple cells when converting to markdown
    table_as_md = parser_output.to_string()
    assert len(re.findall(r"\bCol2\b", table_as_md)) == 4
    assert len(re.findall(r"\bCol3 Col4\b", table_as_md)) == 4
    assert len(re.findall(r"\bCol5\b", table_as_md)) == 4
