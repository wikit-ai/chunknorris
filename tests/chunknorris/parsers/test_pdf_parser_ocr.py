import base64
import http.client
import io
import json
import logging
import urllib.error
from pathlib import Path
from typing import Any

import pymupdf  # type: ignore -> no stubs
import pytest

from chunknorris.chunkers import MarkdownChunker
from chunknorris.exceptions.exceptions import OCRException, PdfParserException
from chunknorris.ml.ocr import MistralOCR, OCRBlock, TesseractOCR
from chunknorris.ml.orientation_classifiers import OrientationPrediction
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


def test_mistral_ocr_checkboxes_are_normalized(
    monkeypatch: pytest.MonkeyPatch, mistral_response: dict[str, Any]
):
    page = mistral_response["pages"][0]
    page["blocks"].append(
        {
            **page["blocks"][-1],
            "type": "text",
            "content": "☑ initial ☐ prolongation □ sans emploi ▢ autre ☒ salarie\n"
            "\\(\\boxed{\\checkmark}\\) Que ce vehicule\n■ bullet",
        }
    )
    _mock_post(monkeypatch, mistral_response)
    parser = PdfParser(ocr_engine=MistralOCR(api_key="test-key"))
    md_string = parser.parse_string(_scanned_document(4)).to_string()

    assert (
        "[x] initial [ ] prolongation [ ] sans emploi [ ] autre [x] salarie"
        in md_string
    )
    assert "[x] Que ce vehicule" in md_string
    # not a checkbox
    assert "■ bullet" in md_string


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
    assert "img-0.jpeg" in chunks_with_images["img-0.jpeg"].to_string()


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


class _StubOrientationClassifier:
    """Predicts the provided (angle, confidence) for each page, in order."""

    def __init__(self, predictions: list[tuple[int, float]]) -> None:
        self.predictions = predictions

    def predict(self, images: list[Any]) -> list[OrientationPrediction]:
        assert len(images) == len(self.predictions)
        return [
            OrientationPrediction(
                angle=angle,
                confidence=confidence,
                is_confident=confidence >= 0.7,
                probabilities={angle: confidence},
            )
            for angle, confidence in self.predictions
        ]


def test_orientation_classifier_turns_pages_upright(
    monkeypatch: pytest.MonkeyPatch, mistral_response: dict[str, Any]
):
    payloads = _mock_post(monkeypatch, mistral_response)
    parser = PdfParser(ocr_engine=MistralOCR(api_key="test-key"))
    # as loaded by detect_orientation=True
    parser.orientation_classifier = _StubOrientationClassifier(  # type: ignore -> stub
        [(0, 0.9), (90, 0.9), (180, 0.5), (270, 0.9)]
    )
    md_doc = parser.parse_string(_scanned_document(4))

    data_uri: str = payloads[0]["document"]["document_url"]
    sent = pymupdf.open("pdf", base64.b64decode(data_uri.split(",", 1)[1]))
    # not confident about page 2: left as is
    assert [page.rotation for page in sent] == [0, 270, 0, 90]  # type: ignore -> missing typing
    assert md_doc.metadata["ocr"]["rotations"] == {1: 90, 3: 270}

    parser.cleanup_memory()
    assert not parser.ocr_rotations


def test_no_rotations_metadata_without_detect_orientation(
    mistral_parser: PdfParser,
):
    md_doc = mistral_parser.parse_string(_scanned_document(4))
    assert "rotations" not in md_doc.metadata["ocr"]


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
    assert "confidence_scores_granularity" not in payload
    assert MistralOCR(api_key="k")._build_payload(b"%PDF")["bbox_annotation_format"]  # type: ignore -> private method


def test_mistral_ocr_confidence(
    monkeypatch: pytest.MonkeyPatch, mistral_response: dict[str, Any]
):
    for page in mistral_response["pages"]:
        for block in page["blocks"]:
            block["confidence_scores"] = {
                "average_content_confidence_score": (
                    None if block["type"] in ("image", "signature") else 0.9
                ),
                "minimum_content_confidence_score": (
                    None if block["type"] in ("image", "signature") else 0.5
                ),
                "block_type_confidence_score": 0.8,
            }
    payloads = _mock_post(monkeypatch, mistral_response)
    engine = MistralOCR(api_key="test-key", return_confidence=True)
    ocr_document = engine.ocr_document(pymupdf.open(stream=_scanned_document(4)), 0, 4)

    assert payloads[0]["confidence_scores_granularity"] == "block"
    assert all(block.type_confidence == 0.8 for block in ocr_document.blocks)
    signature = next(b for b in ocr_document.blocks if b.type == "signature")
    assert signature.content_confidence is None
    assert signature.confidence == 0.8
    title = next(b for b in ocr_document.blocks if b.type == "title")
    assert (title.content_confidence, title.min_content_confidence) == (0.9, 0.5)
    assert title.confidence == pytest.approx(0.4)
    assert OCRBlock("text", "text", pymupdf.Rect(), 0).confidence is None


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


def test_mistral_ocr_honors_retry_after(monkeypatch: pytest.MonkeyPatch):
    sleeps: list[float] = []
    responses: list[Any] = [
        urllib.error.HTTPError("url", 429, "Too Many Requests", {"Retry-After": "12"}, io.BytesIO(b"")),  # type: ignore -> hdrs typing
        urllib.error.HTTPError("url", 503, "Unavailable", {"Retry-After": "3600"}, io.BytesIO(b"")),  # type: ignore -> hdrs typing
        io.BytesIO(b'{"pages": []}'),
    ]

    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", sleeps.append)

    assert MistralOCR(api_key="k")._post({}) == {"pages": []}  # type: ignore -> private method
    assert sleeps == [12.0, 60.0]


@pytest.mark.parametrize(
    "error",
    [
        ConnectionResetError("reset by peer"),
        http.client.IncompleteRead(b"{"),
        TimeoutError("timed out"),
    ],
)
def test_mistral_ocr_retries_on_network_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception
):
    calls: list[int] = []

    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        calls.append(1)
        if len(calls) == 1:
            raise error
        return io.BytesIO(b'{"pages": []}')

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert MistralOCR(api_key="k")._post({}) == {"pages": []}  # type: ignore -> private method
    assert len(calls) == 2


def test_mistral_ocr_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch):
    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        raise ConnectionResetError("reset by peer")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    with pytest.raises(OCRException, match="reset by peer"):
        MistralOCR(api_key="k", max_retries=2)._post({})  # type: ignore -> private method


def test_mistral_ocr_raises_on_invalid_response(monkeypatch: pytest.MonkeyPatch):
    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        return io.BytesIO(b"<html>Bad Gateway</html>")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(OCRException, match="invalid response"):
        MistralOCR(api_key="k")._post({})  # type: ignore -> private method


def test_mistral_ocr_uses_custom_api_url(monkeypatch: pytest.MonkeyPatch):
    urls: list[str] = []

    def urlopen(request: Any, timeout: float) -> io.BytesIO:
        urls.append(request.full_url)
        return io.BytesIO(b'{"pages": []}')

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    MistralOCR(api_key="k", api_url="https://proxy.example.com/v1/ocr")._post({})  # type: ignore -> private method
    assert urls == ["https://proxy.example.com/v1/ocr"]


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
