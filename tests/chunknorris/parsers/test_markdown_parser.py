from chunknorris.parsers import MarkdownParser
from chunknorris.parsers.markdown.components import MarkdownDoc


def test_markdowndoc(md_strings_in: list[str]):
    for string in md_strings_in:
        assert MarkdownDoc.from_string(string).to_string() == string


def test_markdowndoc_from_string(md_with_code_block: str):
    doc = MarkdownDoc.from_string(md_with_code_block)
    assert sum((line.isin_code_block for line in doc.content)) == 3


def test_convert_setext_to_atx(md_standard_setext_in: str, md_standard_setext_out: str):
    assert (
        MarkdownParser.convert_setext_to_atx(md_standard_setext_in)
        == md_standard_setext_out
    )


def test_parse_metadata(md_with_metadata: str):
    content, metadata = MarkdownParser.parse_metadata(md_with_metadata)
    assert content == "markdown content"
    assert metadata == {"metadatakey": "metadatavalue"}


def test_parse_string(
    md_parser: MarkdownParser,
    md_standard_setext_in: str,
    md_standard_setext_out: str,
):
    parser_output = md_parser.parse_string(md_standard_setext_in)
    assert isinstance(parser_output, MarkdownDoc)
    assert parser_output.to_string() == md_standard_setext_out


def test_parse_file(md_parser: MarkdownParser, md_filepath: str):
    parser_output = md_parser.parse_file(md_filepath)
    assert isinstance(parser_output, MarkdownDoc)
