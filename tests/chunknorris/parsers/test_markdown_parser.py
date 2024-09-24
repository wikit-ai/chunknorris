from chunknorris.parsers import MarkdownParser
from chunknorris.types import MarkdownString


def test_parse_string(
    md_parser: MarkdownParser, md_standard_setext_in: str, md_standard_setext_out: str
):
    md_string = md_parser.parse_string(md_standard_setext_in)
    assert isinstance(md_string, MarkdownString)
    assert md_string.content == md_standard_setext_out


def test_parse_file(md_parser: MarkdownParser, md_filepath: str):
    md_string = md_parser.parse_file(md_filepath)
    assert isinstance(md_string, MarkdownString)


def test_convert_setext_to_atx(md_standard_setext_in: str, md_standard_setext_out: str):
    assert (
        MarkdownParser.convert_setext_to_atx(md_standard_setext_in)
        == md_standard_setext_out
    )
