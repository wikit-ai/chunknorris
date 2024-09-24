import pytest
from chunknorris.chunkers import MarkdownChunker
from chunknorris.parsers import WikitJsonParser, MarkdownParser
from chunknorris.pipelines import WikitJsonPipeline


def test_init(
    wikit_parser: WikitJsonParser,
    md_parser: MarkdownParser,
    md_chunker: MarkdownChunker,
):
    # Should pass
    wikit_pipeline = WikitJsonPipeline(wikit_parser, md_chunker)  # type: ignore : just instanciated to validate init.
    # Should not pass (test succeed if ValueError)
    with pytest.raises(ValueError):
        WikitJsonPipeline(md_parser, md_chunker)


def test_chunk_and_save(
    wikit_parser: WikitJsonParser,
    md_chunker: MarkdownChunker,
    wikitjson_md_filepath: str,
):
    wikit_pipeline = WikitJsonPipeline(wikit_parser, md_chunker)
    wikit_pipeline.chunk_and_save(wikitjson_md_filepath)
