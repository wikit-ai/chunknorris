from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import CSVParser


def test_parse_file(csv_parser: CSVParser, csv_filepath: str):

    csv_parser.output_format = "json_lines"
    parser_output = csv_parser.parse_file(csv_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    assert all(line.text.startswith("{") for line in parser_output.content if line.text)

    csv_parser.output_format = "markdown_table"
    parser_output = csv_parser.parse_file(csv_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    assert all(line.text.startswith("|") for line in parser_output.content)


def test_parse_string(csv_parser: CSVParser, csv_filepath: str):
    with open(csv_filepath, "r", encoding="utf-8") as f:
        file_content = f.read()
    parser_output = csv_parser.parse_string(file_content)
    assert isinstance(parser_output, MarkdownDoc)
