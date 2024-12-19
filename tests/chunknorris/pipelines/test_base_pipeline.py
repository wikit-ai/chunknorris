from chunknorris.chunkers import MarkdownChunker
from chunknorris.parsers import HTMLParser, MarkdownParser
from chunknorris.pipelines import BasePipeline


def test_chunk_string_md_to_md(
    md_parser: MarkdownParser,
    md_chunker: MarkdownChunker,
    md_standard_setext_in: str,
    md_standard_out: str,
):
    md_to_md_pipeline = BasePipeline(md_parser, md_chunker)
    chunks = md_to_md_pipeline.chunk_string(md_standard_setext_in)
    assert [chunk.get_text() for chunk in chunks] == md_standard_out


def test_chunk_string_html_to_md(
    html_parser: HTMLParser,
    md_chunker: MarkdownChunker,
    html_string_in: str,
    html_string_out: str,
):
    html_to_md_pipeline = BasePipeline(html_parser, md_chunker)
    chunks = html_to_md_pipeline.chunk_string(html_string_in)
    assert [chunk.get_text() for chunk in chunks] == [html_string_out]
