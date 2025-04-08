from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import CSVParser


def test_parse_file(csv_parser: CSVParser, csv_filepath: str):
    parser_output = csv_parser.parse_file(csv_filepath)
    assert isinstance(parser_output, MarkdownDoc)


def test_parse_string(csv_parser: CSVParser, csv_filepath: str):
    with open(csv_filepath, "r") as f:
        file_content = f.read()
    parser_output = csv_parser.parse_string(file_content)
    assert isinstance(parser_output, MarkdownDoc)
