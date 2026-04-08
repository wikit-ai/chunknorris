import re

import pymupdf  # type: ignore -> no stubs
from PIL.Image import Image as PILImage

from chunknorris import set_ml_backend
from chunknorris.core.components import MarkdownDoc
from chunknorris.ml.pdf_page_classifiers.classifier_onnx import PDFPageClassifierONNX
from chunknorris.ml.pdf_page_classifiers.classifier_ov import PDFPageClassifierOV
from chunknorris.parsers import PdfParser


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


def test_set_ml_backend():
    set_ml_backend("openvino")
    parser = PdfParser(enable_ml_features=True)
    isinstance(parser._page_classifier, PDFPageClassifierOV)
    set_ml_backend("onnx")
    parser = PdfParser(enable_ml_features=True)
    isinstance(parser._page_classifier, PDFPageClassifierONNX)


def test_classify_pages(pdf_filepath: str):
    parser = PdfParser(enable_ml_features=True)
    parser.read_file(pdf_filepath)
    preds = parser.classify_pages()
    assert len(preds) == parser.document.page_count  # type: ignore
