from chunknorris.chunkers import MarkdownChunker
from chunknorris.parsers import HTMLParser, MarkdownParser, PdfParser
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


def test_chunk_file_pdf_to_md(
    pdf_parser: PdfParser,
    md_chunker: MarkdownChunker,
    pdf_filepath: str,
):
    pdf_pipeline = BasePipeline(pdf_parser, md_chunker)
    chunks = pdf_pipeline.chunk_file(pdf_filepath)
    assert len(chunks) == 11
