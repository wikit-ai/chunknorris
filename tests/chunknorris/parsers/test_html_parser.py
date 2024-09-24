from chunknorris.parsers import HTMLParser
from chunknorris.types import MarkdownString


def test_parse_string(
    html_parser: HTMLParser, html_string_in: str, html_string_out: str
):
    md_string = html_parser.parse_string(html_string_in)
    assert isinstance(md_string, MarkdownString)
    assert md_string.content == html_string_out


def test_parse_file(html_parser: HTMLParser, html_filepath: str):
    md_string = html_parser.parse_file(html_filepath)
    assert isinstance(md_string, MarkdownString)
