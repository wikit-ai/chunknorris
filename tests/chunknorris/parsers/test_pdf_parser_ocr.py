import io
import json
import logging
import urllib.error
from pathlib import Path
from typing import Any

import pymupdf  # type: ignore -> no stubs
import pytest

from chunknorris.chunkers import MarkdownChunker
from chunknorris.exceptions.exceptions import PdfParserException
from chunknorris.ml.ocr import MistralOCR, TesseractOCR
from chunknorris.parsers import PdfParser

# Trimmed response of Mistral OCR: 2 pages of company statutes (titles, signature),
# 1 page with a captioned screenshot and running headers/footers, 1 page with tables.
MISTRAL_RESPONSE_FILEPATH = (
    Path(__file__).parents[2] / "test_files" / "ocr" / "mistral_ocr_response.json"
)


@pytest.fixture
def mistral_response() -> dict[str, Any]:
    with open(MISTRAL_RESPONSE_FILEPATH, encoding="utf-8") as f:
        return json.load(f)


def _scanned_document(page_count: int) -> bytes:
    """A document made of pages holding a single page-sized image, as a scanner produces."""
    doc = pymupdf.open()
    for _ in range(page_count):
        page = doc.new_page()  # type: ignore -> missing typing : Document.new_page() -> Page
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 800))
        pixmap.clear_with(210)  # type: ignore -> missing typing
        page.insert_image(page.rect, pixmap=pixmap)  # type: ignore -> missing typing
    return doc.tobytes()  # type: ignore -> missing typing


def _mock_post(
    monkeypatch: pytest.MonkeyPatch, response: dict[str, Any]
) -> list[dict[str, Any]]:
    """Replaces the API call by the provided response. Returns the list of sent payloads."""
    payloads: list[dict[str, Any]] = []

    def post(self: MistralOCR, payload: dict[str, Any]) -> dict[str, Any]:
        payloads.append(payload)
        return response

    monkeypatch.setattr(MistralOCR, "_post", post)
    return payloads


@pytest.fixture
def mistral_parser(
    monkeypatch: pytest.MonkeyPatch, mistral_response: dict[str, Any]
) -> PdfParser:
    _mock_post(monkeypatch, mistral_response)
    return PdfParser(ocr_engine=MistralOCR(api_key="test-key"))


def test_mistral_ocr_on_scanned_document(mistral_parser: PdfParser):
    md_doc = mistral_parser.parse_string(_scanned_document(4))
    md_string = md_doc.to_string()

    assert mistral_parser.parsed_using_ocr
    assert md_doc.metadata["ocr"] == {
        "engine": "mistral",
        "model": "mistral-ocr-4-1",
        "pages": [0, 1, 2, 3],
    }
    assert md_string.startswith("# STATUTS\n")
    assert {line.page for line in md_doc.content} == {0, 1, 2, 3}
    # tables are kept as returned by the OCR
    assert "|  Name | Type | Difficulty |" in md_string


def test_mistral_ocr_headers_are_shifted_below_main_title(mistral_parser: PdfParser):
    md_doc = mistral_parser.parse_string(_scanned_document(4))
    header_levels = [
        line.get_header_level() for line in md_doc.content if line.is_header
    ]

    assert mistral_parser.main_title == "STATUTS"
    assert "## Article 1 – Forme" in md_doc.to_string()
    assert header_levels.count(1) == 1


def test_mistral_ocr_headers_footers_are_removed(mistral_parser: PdfParser):
    md_string = mistral_parser.parse_string(_scanned_document(4)).to_string()

    assert "WWW.LAKERA.AI" not in md_string
    assert "4428081.3" not in md_string


def test_mistral_ocr_images(mistral_parser: PdfParser):
    md_doc = mistral_parser.parse_string(_scanned_document(4))
    md_string = md_doc.to_string()

    assert set(md_doc.images) == {"signature-0", "img-0.jpeg"}
    screenshot = md_doc.images["img-0.jpeg"]
    assert screenshot.image_type == "screenshot"
    assert screenshot.page == 2
    assert screenshot.caption and screenshot.caption.startswith("Application: Gmail")
    assert (
        f"![screenshot](img-0.jpeg)\n> {screenshot.caption.splitlines()[0]}"
        in md_string
    )
    # signatures have no caption, only a location
    signature = md_doc.images["signature-0"]
    assert signature.caption is None and signature.bbox is not None
    assert "![signature](signature-0)" in md_string


def test_mistral_ocr_images_survive_chunking(mistral_parser: PdfParser):
    md_doc = mistral_parser.parse_string(_scanned_document(4))
    chunks = MarkdownChunker(min_chunk_word_count=0).chunk(md_doc)

    chunks_with_images = {
        image_id: chunk for chunk in chunks for image_id in chunk.images
    }
    assert set(chunks_with_images) == {"signature-0", "img-0.jpeg"}
    assert "img-0.jpeg" in chunks_with_images["img-0.jpeg"].get_text()


def test_mistral_ocr_skip_image_types(
    monkeypatch: pytest.MonkeyPatch, mistral_response: dict[str, Any]
):
    _mock_post(monkeypatch, mistral_response)
    parser = PdfParser(
        ocr_engine=MistralOCR(api_key="test-key", skip_image_types=["screenshot"])
    )
    md_doc = parser.parse_string(_scanned_document(4))

    assert "img-0.jpeg" not in md_doc.images
    assert "img-0.jpeg" not in md_doc.to_string()


def test_mistral_ocr_native_text_is_not_ocred(mistral_parser: PdfParser):
    """With use_ocr="auto", the document OCR only runs if no text is found."""
    doc = pymupdf.open()
    page = doc.new_page()  # type: ignore -> missing typing
    for i in range(20):
        page.insert_text((50, 80 + i * 18), f"Ligne {i} de contenu reel.", fontsize=11)  # type: ignore -> missing typing

    md_doc = mistral_parser.parse_string(doc.tobytes())  # type: ignore -> missing typing

    assert not mistral_parser.parsed_using_ocr
    assert "ocr" not in md_doc.metadata
    assert "Ligne 0 de contenu reel." in md_doc.to_string()


def test_mistral_ocr_native_parsing_methods_are_guarded(mistral_parser: PdfParser):
    mistral_parser.parse_string(_scanned_document(4))

    with pytest.raises(PdfParserException):
        mistral_parser.get_toc()
    with pytest.raises(PdfParserException):
        mistral_parser.get_tables()


def test_mistral_ocr_state_is_reset_between_documents(mistral_parser: PdfParser):
    mistral_parser.parse_string(_scanned_document(4))
    mistral_parser.cleanup_memory()

    assert not mistral_parser.parsed_using_ocr
    assert not mistral_parser.ocr_blocks and not mistral_parser.ocr_images


def test_mistral_ocr_splits_heavy_documents(
    monkeypatch: pytest.MonkeyPatch, mistral_response: dict[str, Any]
):
    """Documents heavier than max_request_mb are sent over several requests,
    and the page numbers of the responses are offset accordingly."""
    single_page_response = {**mistral_response, "pages": mistral_response["pages"][:1]}
    payloads = _mock_post(monkeypatch, single_page_response)
    engine = MistralOCR(api_key="test-key", max_request_mb=0)
    document = pymupdf.open(stream=_scanned_document(3), filetype="pdf")

    ocr_document = engine.ocr_document(document, 0, 3)

    assert len(payloads) == 3
    assert ocr_document.pages == [0, 1, 2]
    assert {block.page for block in ocr_document.blocks} == {0, 1, 2}
    assert [block.order for block in ocr_document.blocks] == list(
        range(len(ocr_document.blocks))
    )


def test_mistral_ocr_payload():
    engine = MistralOCR(api_key="test-key", image_captioning=False, store_images=True)
    payload = engine._build_payload(b"%PDF")  # type: ignore -> private method

    assert payload["model"] == "mistral-ocr-4-1"
    assert payload["include_blocks"] is True
    assert payload["include_image_base64"] is True
    assert "bbox_annotation_format" not in payload
    assert MistralOCR(api_key="k")._build_payload(b"%PDF")["bbox_annotation_format"]  # type: ignore -> private method


def test_mistral_ocr_retries_on_rate_limit(monkeypatch: pytest.MonkeyPatch):
    calls: list[int] = []

    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError("url", 429, "Too Many Requests", {}, io.BytesIO(b""))  # type: ignore -> hdrs typing
        return io.BytesIO(b'{"pages": []}')

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert MistralOCR(api_key="k")._post({}) == {"pages": []}  # type: ignore -> private method
    assert len(calls) == 2


def test_mistral_ocr_raises_on_client_error(monkeypatch: pytest.MonkeyPatch):
    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, io.BytesIO(b"bad key"))  # type: ignore -> hdrs typing

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(PdfParserException, match="401"):
        MistralOCR(api_key="k", max_retries=3)._post({})  # type: ignore -> private method


def test_mistral_ocr_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    with pytest.raises(PdfParserException):
        PdfParser(ocr_engine=MistralOCR())


def test_mistral_ocr_rejects_unknown_image_types():
    with pytest.raises(ValueError):
        MistralOCR(skip_image_types=["selfie"])


def test_ocr_language_is_deprecated():
    with pytest.warns(DeprecationWarning):
        parser = PdfParser(use_ocr="never", ocr_language="eng")

    assert isinstance(parser.ocr_engine, TesseractOCR)
    assert parser.ocr_language == "eng"


def test_ocr_language_conflicts_with_ocr_engine():
    with pytest.raises(ValueError):
        PdfParser(
            use_ocr="never",
            ocr_engine=TesseractOCR(language="eng"),
            ocr_language="fra",
        )


def test_mistral_ocr_is_logged(
    mistral_parser: PdfParser, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.INFO, logger="ChunkNorris"):
        mistral_parser.parse_string(_scanned_document(4))

    assert any(
        record.levelno == logging.INFO and "Running OCR" in record.getMessage()
        for record in caplog.records
    )
