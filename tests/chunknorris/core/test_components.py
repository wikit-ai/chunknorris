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


@pytest.mark.parametrize(
    "md_string",
    [
        # image within a link
        "Intro [![build](https://x.io/b.svg)](https://ci.io) text.",
        # image within a table cell
        "| logo | name |\n|---|---|\n| ![logo](a.png) | foo |",
        # image within a sentence
        "Click the ![icon](i.png) button.",
        # image opening a list item
        "- ![a](a.png)\n- item",
        # image within a code block
        "```md\nsee ![x](y.png) here\n```",
    ],
)
def test_to_string_keeps_non_standalone_images_in_place(md_string: str):
    md_doc = MarkdownDoc.from_string(md_string)
    assert md_doc.to_string() == md_string


def test_to_string_isolates_standalone_images():
    md_doc = MarkdownDoc.from_string(
        "Text\n![a](a.png)\n> caption\nafter\n![b](b.png)\n![c](c.png)"
    )
    assert md_doc.to_string() == (
        "Text\n\n![a](a.png)\n> caption\n\nafter\n\n![b](b.png)\n\n![c](c.png)"
    )


def test_to_string_include_images_skips_code_blocks():
    md_doc = MarkdownDoc.from_string("```md\n![x](img-0.png)\n```")
    md_doc.images = {
        "img-0.png": DocImage(id="img-0.png", base64="data:image/png;base64,AAA")
    }
    assert md_doc.to_string(include_images=True) == "```md\n![x](img-0.png)\n```"


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
