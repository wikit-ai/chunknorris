from chunknorris.chunkers import MarkdownChunker
from chunknorris.core.markdown_images import extract_images
from chunknorris.parsers import DocxParser, HTMLParser, MarkdownParser

PNG = "data:image/png;base64,iVBORw0KGgo="
SVG = "data:image/svg+xml;base64,PHN2Zz4="


def test_extract_embedded_images():
    md, images = extract_images(f"![logo]({PNG})\n\n![same]({PNG})\n\n![icon]({SVG})")
    assert md == "![logo](img-0.png)\n\n![same](img-0.png)\n\n![icon](img-1.svg)"
    assert images["img-0.png"].base64 == PNG
    assert images["img-1.svg"].base64 == SVG


def test_extract_url_images():
    md, images = extract_images(
        '![a](https://x.org/a_(1).png "title") ![b](<./my files/b.png>)'
    )
    assert md == "![a](https://x.org/a_%281%29.png) ![b](./my%20files/b.png)"
    assert set(images) == {"https://x.org/a_%281%29.png", "./my%20files/b.png"}
    assert all(image.base64 is None for image in images.values())


def test_extract_reference_images():
    md, images = extract_images(
        f"![one][r1] ![Two][]\n\n[r1]: {PNG}\n[two]: https://x.org/b.png\n[link]: https://x.org"
    )
    # data URI definitions are removed, the others may be used by links
    assert md == (
        "![one](img-0.png) ![Two](https://x.org/b.png)\n\n"
        "[two]: https://x.org/b.png\n[link]: https://x.org"
    )
    assert set(images) == {"img-0.png", "https://x.org/b.png"}


def test_extract_caption():
    _, images = extract_images(f"![chart]({PNG})\n> Sales\n> by year\n\nText")
    assert images["img-0.png"].caption == "Sales\nby year"


def test_extract_ignores_code_blocks():
    md, images = extract_images("```md\n![a](https://x.org/a.png)\n```")
    assert md == "```md\n![a](https://x.org/a.png)\n```"
    assert images == {}


def test_extract_removes_stray_data_uris():
    md, images = extract_images(f'<img src="{PNG}"> and ![empty]()')
    assert md == '<img src=""> and '
    assert images == {}


def test_markdown_parser_round_trip(md_parser: MarkdownParser):
    md_doc = md_parser.parse_string(f"# Title\n\n![chart]({PNG})\n> Sales by year")
    assert md_doc.to_string() == "# Title\n\n![chart](img-0.png)\n> Sales by year"
    reparsed = md_parser.parse_string(md_doc.to_string(include_images=True))
    assert reparsed.images == md_doc.images
    assert reparsed.to_string() == md_doc.to_string()


def test_html_parser_images(html_parser: HTMLParser):
    md_doc = html_parser.parse_string(f"""<p>Text</p>
        <figure><a href="/file"><img src="{PNG}" alt="A
        chart"></a><figcaption>Sales by <a href="/y">year</a></figcaption></figure>
        <figure><table><tr><td>1</td></tr></table><figcaption>Table</figcaption></figure>
        <h2>Title <img src="icon.png" alt="icon"></h2>
        <ul><li><img src="a.png" alt="A"> item</li></ul>""")
    assert md_doc.to_string() == (
        "Text\n\n"
        "![A chart](img-0.png)\n> Sales by [year](/y)\n\n"
        "| 1 |\n|-----|\n\nTable\n\n"
        "## Title icon\n\n"
        "- ![A](a.png) item"
    )
    assert md_doc.images["img-0.png"].caption == "Sales by [year](/y)"
    assert md_doc.images["img-0.png"].base64 == PNG
    assert set(md_doc.images) == {"img-0.png", "a.png"}


def test_docx_parser_images(docx_parser: DocxParser, docx_filepath: str):
    md_doc = docx_parser.parse_file(docx_filepath)
    assert md_doc.images
    assert all(image.base64 for image in md_doc.images.values())
    assert "base64" not in md_doc.to_string()


def test_chunks_images(md_parser: MarkdownParser):
    md_doc = md_parser.parse_string(
        f"# A\n\n![chart]({PNG})\n> Sales\n\n# B\n\n![logo](https://x.org/logo.png)"
    )
    chunks = MarkdownChunker(min_chunk_word_count=0).chunk(md_doc)
    assert len(chunks) == 1
    assert list(chunks[0].images) == ["img-0.png", "https://x.org/logo.png"]
    assert chunks[0].images["img-0.png"].caption == "Sales"
