import re

import pymupdf  # type: ignore -> no stubs
import pytest
from PIL.Image import Image as PILImage

from chunknorris import set_ml_backend
from chunknorris.core.components import MarkdownDoc
from chunknorris.exceptions.exceptions import TextNotFoundException
from chunknorris.parsers import PdfParser

try:
    from chunknorris.ml.pdf_page_classifiers.classifier_onnx import (
        PDFPageClassifierONNX,
    )
    from chunknorris.ml.pdf_page_classifiers.classifier_ov import PDFPageClassifierOV

    ML_BACKENDS_AVAILABLE = True
except ImportError:  # the ml-onnx / ml-openvino extras are not installed
    ML_BACKENDS_AVAILABLE = False

requires_ml_backends = pytest.mark.skipif(
    not ML_BACKENDS_AVAILABLE,
    reason="requires the ml-onnx and ml-openvino extras",
)


def test_parse_file(pdf_parser: PdfParser, pdf_filepath: str):
    parser_output = pdf_parser.parse_file(pdf_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    # Assert header and footers have been detected
    assert len([span for span in pdf_parser.spans if span.is_header_footer]) > 0
    ### Table parsing ###
    # Assert the table has been detected and no false detection
    assert len(pdf_parser.tables) == 1
    # Assert teble cells have been parsed correctly
    assert len(pdf_parser.tables[0].cells) == 18
    # Assert the merged cell are lead to outputing the tables as HTML
    assert len(re.findall("No", pdf_parser.tables[0].to_markdown())) == 2
    ### Table of content detection ###
    # Assert table of content has been found
    assert len(pdf_parser.toc) == 10
    # Assert correct level have been found
    assert (
        len([title for title in pdf_parser.toc if title.level == 2]) == 2
        and len([title for title in pdf_parser.toc if title.level == 1]) == 8
    )
    ### Main Title ###
    assert pdf_parser.main_title == "DUMMY  DOCUMENT  TITLE  Dummy subtitle"
    # Pagination is intact
    assert len(parser_output.to_string(keep_track_of_page=True)) == 10


def test_parse_tables(pdf_parser: PdfParser, pdf_tables_filepath: str):
    _ = pdf_parser.parse_file(pdf_tables_filepath)
    assert len(pdf_parser.tables) == 1
    # Check tables 0 is valid
    assert len(pdf_parser.tables[0].cells) == 18
    assert pdf_parser.tables[0].to_pandas().shape == (4, 5)
    table_0_as_md = pdf_parser.tables[0].to_markdown()
    assert len(re.findall("Col2", table_0_as_md)) == 1
    assert len(re.findall("Col3 Col4", table_0_as_md)) == 1
    assert len(re.findall("Col5", table_0_as_md)) == 3


def test_parse_string(pdf_parser: PdfParser, pdf_filepath: str):
    byte_string = pymupdf.open(pdf_filepath).tobytes()  # type: ignore -> missing typing : pymupdf.open() -> pymupdf.Document
    md_string = pdf_parser.parse_string(byte_string)
    assert isinstance(md_string, MarkdownDoc)


def test_parse_single_line_document(pdf_parser: PdfParser):
    """A document holding a single line of text (e.g. a form with one field
    filled in) yields no consecutive line pair to estimate the body linespacing
    from. It must still parse instead of raising."""
    doc = pymupdf.open()
    page = doc.new_page()  # type: ignore -> missing typing : Document.new_page() -> Page
    page.insert_text((50, 100), "Nom : Chuck Norris", fontsize=11)  # type: ignore -> missing typing

    parser_output = pdf_parser.parse_string(doc.tobytes())  # type: ignore -> missing typing

    assert isinstance(parser_output, MarkdownDoc)
    assert "Nom : Chuck Norris" in parser_output.to_string()
    assert pdf_parser.body_line_spacing == 0.0


def _scanned_page(doc: pymupdf.Document, stamp: str | None = None) -> None:
    """Appends a page made of a single page-sized image, as a scanner produces,
    optionally stamped with a date/page number in the top margin."""
    page = doc.new_page()  # type: ignore -> missing typing : Document.new_page() -> Page
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 800))
    pixmap.clear_with(210)  # type: ignore -> missing typing
    page.insert_image(page.rect, pixmap=pixmap)  # type: ignore -> missing typing
    if stamp is not None:
        page.insert_text((50, 22), stamp, fontsize=7)  # type: ignore -> missing typing


@pytest.mark.parametrize(
    "stamps",
    [
        pytest.param([None, None, None], id="no_stamp"),
        pytest.param(["12/03/2024 09:41"] * 3, id="stamp_same_position"),
        pytest.param(
            [
                "12/03/2024 09:41  Page 1",
                "12/03/2024 09:42  Page 2",
                "13/03/2024 10:03  Page 3",
            ],
            id="stamp_varying",
        ),
        pytest.param(["12/03/2024 09:41"], id="single_page"),
    ],
)
def test_parse_scanned_document_raises(pdf_parser: PdfParser, stamps: list[str | None]):
    """A document whose pages are images carrying at most a scanner stamp holds no
    reachable text: it must ask for OCR rather than return the stamps as content."""
    doc = pymupdf.open()
    for stamp in stamps:
        _scanned_page(doc, stamp)

    with pytest.raises(TextNotFoundException):
        pdf_parser.parse_string(doc.tobytes())  # type: ignore -> missing typing


def test_parse_scanned_document_is_decided_document_wide(pdf_parser: PdfParser):
    """A scanned page sitting next to pages that do hold text must not make the
    whole document look scanned, and neither must a page-sized image carrying a
    real paragraph."""
    doc = pymupdf.open()
    _scanned_page(doc, "12/03/2024 09:41")
    page = doc.new_page()  # type: ignore -> missing typing
    for i in range(20):
        page.insert_text((50, 80 + i * 18), f"Ligne {i} de contenu reel.", fontsize=11)  # type: ignore -> missing typing

    parser_output = pdf_parser.parse_string(doc.tobytes())  # type: ignore -> missing typing

    assert "Ligne 0 de contenu reel." in parser_output.to_string()


def test_parse_section_title_page(pdf_parser: PdfParser):
    """A section divider page holds a single title and needs no OCR."""
    doc = pymupdf.open()
    page = doc.new_page()  # type: ignore -> missing typing
    page.insert_text((50, 300), "Partie 1", fontsize=24)  # type: ignore -> missing typing

    parser_output = pdf_parser.parse_string(doc.tobytes())  # type: ignore -> missing typing

    assert "Partie 1" in parser_output.to_string()


def test_get_pages_as_images(pdf_parser: PdfParser, pdf_filepath: str):
    pdf_parser.read_file(pdf_filepath)

    all_img = pdf_parser.get_pages_as_images(page_numbers=None)
    img_page_5 = pdf_parser.get_pages_as_images(page_numbers=5)
    img_page_567 = pdf_parser.get_pages_as_images(page_numbers=[5, 6, 7])
    assert isinstance(img_page_5, PILImage)
    assert isinstance(all_img, list)
    assert isinstance(img_page_567, list)
    assert len(all_img) == pdf_parser.document.page_count  # type: ignore
    assert len(img_page_567) == 3
    # assert the indexes of page work fine
    assert all_img[5] == img_page_5 == img_page_567[0]


@requires_ml_backends
def test_set_ml_backend():
    set_ml_backend("openvino")
    parser = PdfParser(enable_ml_features=True, use_ocr="never")
    isinstance(parser._page_classifier, PDFPageClassifierOV)
    set_ml_backend("onnx")
    parser = PdfParser(enable_ml_features=True)
    isinstance(parser._page_classifier, PDFPageClassifierONNX)


@requires_ml_backends
def test_classify_pages(pdf_filepath: str):
    parser = PdfParser(enable_ml_features=True, use_ocr="never")
    parser.read_file(pdf_filepath)
    preds = [pred for pred in parser.classify_pages()]
    assert len(preds) == parser.document.page_count  # type: ignore
