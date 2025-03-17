from chunknorris.chunkers import MarkdownChunker
from chunknorris.core.components import Chunk, MarkdownDoc


def test_chunk_string(
    md_chunker: MarkdownChunker,
    md_strings_in: list[str],
    md_strings_out: list[list[str]],
):
    for input, output in zip(md_strings_in, md_strings_out):
        typed_input = MarkdownDoc.from_string(input)
        chunks = md_chunker.chunk(typed_input)
        assert [chunk.get_text() for chunk in chunks] == output


def test_split_big_chunks(md_big_chunk_in: Chunk, md_big_chunk_out: list[str]):
    md_chunker = MarkdownChunker(
        max_chunk_word_count=0, hard_max_chunk_word_count=10, min_chunk_word_count=0
    )
    assert [
        chunk.get_text() for chunk in md_chunker.split_big_chunks([md_big_chunk_in])
    ] == md_big_chunk_out
