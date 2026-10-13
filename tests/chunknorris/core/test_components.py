import pytest

from chunknorris.chunkers import MarkdownChunker
from chunknorris.core.components import Chunk, DocImage, MarkdownDoc, MarkdownLine


# tests : Chunk
def test_to_string(chunk_with_links: Chunk, chunk_with_links_out: str):
    assert chunk_with_links.to_string(remove_links=True) == chunk_with_links_out


def test_get_text_is_deprecated(chunk_with_links: Chunk):
    with pytest.deprecated_call():
        text = chunk_with_links.get_text(remove_links=True)
    assert text == chunk_with_links.to_string(remove_links=True)


def test_to_string_include_images():
    chunk = Chunk(
        headers=[MarkdownLine("# Title", 0)],
        content=[
            MarkdownLine("Some text", 1),
            MarkdownLine("![chart](img-0.jpeg)", 2),
            MarkdownLine("and a [link](a.html)", 3),
        ],
        start_line=1,
        images={
            "img-0.jpeg": DocImage(id="img-0.jpeg", base64="data:image/jpeg;base64,AAA")
        },
    )
    assert chunk.to_string() == (
        "# Title\n\nSome text\n\n![chart](img-0.jpeg)\n\nand a [link](a.html)"
    )
    assert chunk.to_string(
        include_images=True, remove_links=True, prepend_headers=False
    ) == (
        "Some text\n\n![chart][img-0.jpeg]\n\nand a link\n\n"
        "[img-0.jpeg]: data:image/jpeg;base64,AAA"
    )


# tests : TocTree
def test_to_json(md_chunker: MarkdownChunker, md_standard_in: str):
    md_lines = MarkdownDoc.from_string(md_standard_in).content
    toc_tree = md_chunker.get_toc_tree(md_lines)
    toc_tree.to_json()


# tests : MarkdownLine
def test_markdown_line_normalizes_unicode():
    # compatibility characters (non-breaking space, ligature) are folded
    # while accented letters stay composed
    line = MarkdownLine("Arrêt de travail ﬁn", 0)
    assert line.text == "Arrêt de travail fin"
    assert "̂" not in line.text
