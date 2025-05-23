from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import HTMLParser


def test_parse_string(
    html_parser: HTMLParser, html_string_in: str, html_string_out: str
):
    parser_output = html_parser.parse_string(html_string_in)
    assert isinstance(parser_output, MarkdownDoc)
    assert parser_output.to_string() == html_string_out


def test_parse_file(html_parser: HTMLParser, html_filepath: str):
    parser_output = html_parser.parse_file(html_filepath)
    assert isinstance(parser_output, MarkdownDoc)
