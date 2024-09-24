from chunknorris.parsers import WikitJsonParser
from chunknorris.types.types import MarkdownString


def test_parse_string(wikit_parser: WikitJsonParser, json_string_in: str):
    md_string = wikit_parser.parse_string(json_string_in)
    assert isinstance(md_string, MarkdownString)


def test_parse_file(
    wikit_parser: WikitJsonParser,
    wikitjson_md_filepath: str,
    wikitjson_html_filepath: str,
):
    md_string = wikit_parser.parse_file(wikitjson_md_filepath)
    assert isinstance(md_string, MarkdownString)
    md_string = wikit_parser.parse_file(wikitjson_html_filepath)
    assert isinstance(md_string, MarkdownString)
