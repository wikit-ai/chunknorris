import base64
import io
import json
import struct
from pathlib import Path
from typing import Any

import pymupdf  # type: ignore -> no stubs
import pytest
from PIL import Image

from chunknorris.exceptions.exceptions import (
    ImageParserException,
    OCRException,
    PdfParserException,
    TextNotFoundException,
)
from chunknorris.ml.ocr import MistralOCR
from chunknorris.parsers import ImageParser

# Trimmed response of Mistral OCR, see test_pdf_parser_ocr.py
MISTRAL_RESPONSE_FILEPATH = (
    Path(__file__).parents[2] / "test_files" / "ocr" / "mistral_ocr_response.json"
)


def _image(image_format: str = "png") -> bytes:
    """A blank image in the provided format ("png" or "jpg")."""
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 800), 0)
    pixmap.clear_with(210)  # type: ignore -> missing typing
    return pixmap.tobytes(image_format)  # type: ignore -> missing typing


def _tiff(frame_count: int, width: int = 60, height: int = 80) -> bytes:
    """A blank uncompressed grayscale tiff holding the provided number of frames."""
    entry_count = 8
    ifd_size = 2 + entry_count * 12 + 4
    frame_size = ifd_size + width * height
    data = b"II*\x00" + struct.pack("<I", 8)
    for frame in range(frame_count):
        ifd_offset = 8 + frame * frame_size
        next_ifd_offset = ifd_offset + frame_size if frame < frame_count - 1 else 0
        entries = [  # (tag, type, value), type 3 = short, 4 = long
            (256, 4, width),
            (257, 4, height),
            (258, 3, 8),  # bits per sample
            (259, 3, 1),  # no compression
            (262, 3, 1),  # black is zero
            (273, 4, ifd_offset + ifd_size),  # strip offset
            (278, 4, height),  # rows per strip
            (279, 4, width * height),  # strip byte count
        ]
        data += struct.pack("<H", entry_count)
        for tag, value_type, value in entries:
            data += struct.pack("<HHII", tag, value_type, 1, value)
        data += struct.pack("<I", next_ifd_offset) + b"\xd2" * (width * height)
    return data


def _mock_post(
    monkeypatch: pytest.MonkeyPatch, page_count: int, empty: bool = False
) -> list[dict[str, Any]]:
    """Replaces the API call by the first pages of the trimmed response.
    Returns the list of sent payloads."""
    with open(MISTRAL_RESPONSE_FILEPATH, encoding="utf-8") as f:
        response = json.load(f)
    response["pages"] = response["pages"][:page_count]
    if empty:
        for page in response["pages"]:
            page["blocks"], page["images"] = [], []
            page["markdown"] = ""
    payloads: list[dict[str, Any]] = []

    def post(self: MistralOCR, payload: dict[str, Any]) -> dict[str, Any]:
        payloads.append(payload)
        return response

    monkeypatch.setattr(MistralOCR, "_post", post)
    return payloads


@pytest.fixture
def parser() -> ImageParser:
    return ImageParser(ocr_engine=MistralOCR(api_key="test-key"))


def _sent_document(payload: dict[str, Any]) -> pymupdf.Document:
    data_uri: str = payload["document"]["document_url"]
    prefix = "data:application/pdf;base64,"
    assert data_uri.startswith(prefix)
    return pymupdf.open("pdf", base64.b64decode(data_uri.removeprefix(prefix)))


def test_parse_string(monkeypatch: pytest.MonkeyPatch, parser: ImageParser):
    payloads = _mock_post(monkeypatch, page_count=1)
    md_doc = parser.parse_string(_image())

    assert parser.parsed_using_ocr
    assert md_doc.metadata["ocr"] == {
        "engine": "mistral",
        "model": "mistral-ocr-4-1",
        "pages": [0],
    }
    assert md_doc.to_string().startswith("# STATUTS\n")
    # the image is sent as a single page pdf
    assert _sent_document(payloads[0]).page_count == 1  # type: ignore -> missing typing


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "L", "P", "CMYK"])
def test_parse_image(monkeypatch: pytest.MonkeyPatch, parser: ImageParser, mode: str):
    payloads = _mock_post(monkeypatch, page_count=1)
    md_doc = parser.parse_image(Image.new(mode, (600, 800)))

    assert md_doc.to_string().startswith("# STATUTS\n")
    assert _sent_document(payloads[0]).page_count == 1  # type: ignore -> missing typing


def test_parse_multi_frame_image(monkeypatch: pytest.MonkeyPatch, parser: ImageParser):
    payloads = _mock_post(monkeypatch, page_count=2)
    image = Image.open(io.BytesIO(_tiff(frame_count=2)))
    md_doc = parser.parse_image(image)

    assert _sent_document(payloads[0]).page_count == 2  # type: ignore -> missing typing
    assert md_doc.metadata["ocr"]["pages"] == [0, 1]


@pytest.mark.parametrize("extension", [".png", ".jpg", ".JPEG", ".tiff"])
def test_parse_file(
    monkeypatch: pytest.MonkeyPatch,
    parser: ImageParser,
    tmp_path: Path,
    extension: str,
):
    _mock_post(monkeypatch, page_count=1)
    images = {".png": _image("png"), ".jpg": _image("jpg"), ".jpeg": _image("jpg")}
    filepath = tmp_path / f"image{extension}"
    filepath.write_bytes(images.get(extension.lower()) or _tiff(frame_count=1))
    md_doc = parser.parse_file(str(filepath))

    assert parser.filepath == str(filepath)
    assert md_doc.to_string().startswith("# STATUTS\n")


def test_multi_frame_image_is_parsed_as_multi_page(
    monkeypatch: pytest.MonkeyPatch, parser: ImageParser
):
    payloads = _mock_post(monkeypatch, page_count=2)
    md_doc = parser.parse_string(_tiff(frame_count=2))

    assert _sent_document(payloads[0]).page_count == 2  # type: ignore -> missing typing
    assert md_doc.metadata["ocr"]["pages"] == [0, 1]


def test_image_without_text_raises(
    monkeypatch: pytest.MonkeyPatch, parser: ImageParser
):
    _mock_post(monkeypatch, page_count=1, empty=True)
    with pytest.raises(TextNotFoundException):
        parser.parse_string(_image())


def test_rejects_unsupported_extension(parser: ImageParser, tmp_path: Path):
    filepath = tmp_path / "image.webp"
    filepath.write_bytes(_image())
    with pytest.raises(ImageParserException, match="Only"):
        parser.parse_file(str(filepath))


def test_rejects_pdf(parser: ImageParser):
    document = pymupdf.open()
    document.new_page()  # type: ignore -> missing typing
    with pytest.raises(ImageParserException, match="'PDF"):
        parser.parse_string(document.tobytes())  # type: ignore -> missing typing


def test_rejects_invalid_bytes(parser: ImageParser):
    with pytest.raises(ImageParserException):
        parser.parse_string(b"not an image")


def test_ocr_errors_are_ocr_exceptions(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(OCRException) as exc_info:
        ImageParser(ocr_engine=MistralOCR())
    # backward compatibility
    assert isinstance(exc_info.value, PdfParserException)
