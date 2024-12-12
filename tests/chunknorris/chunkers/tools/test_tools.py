from chunknorris.chunkers import MarkdownChunker
from chunknorris.chunkers.tools import Chunk
from chunknorris.parsers.markdown.components import MarkdownDoc


# tests : Chunk
def test_get_text(chunk_with_links: Chunk, chunk_with_links_out: str):
    assert chunk_with_links.get_text(remove_links=True) == chunk_with_links_out


# tests : TocTree
def test_to_json(md_chunker: MarkdownChunker, md_standard_in: str):
    md_lines = MarkdownDoc.from_string(md_standard_in).content
    toc_tree = md_chunker.get_toc_tree(md_lines)
    toc_tree.to_json()
