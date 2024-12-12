import pytest

from chunknorris.chunkers import MarkdownChunker
from chunknorris.parsers import PdfParser
from chunknorris.pipelines import PdfPipeline


def test_init(
    pdf_parser: PdfParser,
    md_chunker: MarkdownChunker,
):
    # Should pass
    _ = PdfPipeline(pdf_parser, md_chunker)  # type: ignore : just instanciated to validate init.
    # Should not pass (test succeed if ValueError)
    with pytest.raises(ValueError):
        PdfPipeline(md_chunker, md_chunker)


def test_chunk_file(
    pdf_parser: PdfParser,
    md_chunker: MarkdownChunker,
    pdf_filepath: str,
):
    pdf_pipeline = PdfPipeline(pdf_parser, md_chunker)
    chunks = pdf_pipeline.chunk_file(pdf_filepath)
    assert len(chunks) == 11
