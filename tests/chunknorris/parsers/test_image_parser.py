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
from chunknorris.ml.orientation_classifiers import OrientationPrediction
from chunknorris.parsers import ImageParser

# Trimmed response of Mistral OCR, see test_pdf_parser_ocr.py
MISTRAL_RESPONSE_FILEPATH = (
    Path(__file__).parents[2] / "test_files" / "ocr" / "mistral_ocr_response.json"
)


def _image(image_format: str = "png", width: int = 600, height: int = 800) -> bytes:
    """A blank image in the provided format ("png" or "jpg")."""
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), 0)
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
    monkeypatch: pytest.MonkeyPatch, empty: bool = False
) -> list[dict[str, Any]]:
    """Replaces the API call by the first page of the trimmed response,
    as each frame is sent in its own request. Returns the list of sent payloads."""
    with open(MISTRAL_RESPONSE_FILEPATH, encoding="utf-8") as f:
        response = json.load(f)
    response["pages"] = response["pages"][:1]
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


def _sent_image(payload: dict[str, Any]) -> tuple[str, pymupdf.Pixmap]:
    """The mime type and the content of the image sent in the payload."""
    assert payload["document"]["type"] == "image_url"
    data_uri: str = payload["document"]["image_url"]
    header, data = data_uri.split(";base64,")
    return header.removeprefix("data:"), pymupdf.Pixmap(base64.b64decode(data))


def _sent_size(payload: dict[str, Any]) -> tuple[int, int]:
    pixmap = _sent_image(payload)[1]
    return pixmap.width, pixmap.height  # type: ignore -> missing typing


class _StubOrientationClassifier:
    def __init__(self, angle: int) -> None:
        self.angle = angle

    def predict(self, images: list[Any]) -> list[OrientationPrediction]:
        return [
            OrientationPrediction(
                angle=self.angle,
                confidence=0.9,
                is_confident=True,
                probabilities={self.angle: 0.9},
            )
            for _ in images
        ]


def test_parse_string(monkeypatch: pytest.MonkeyPatch, parser: ImageParser):
    payloads = _mock_post(monkeypatch)
    md_doc = parser.parse_string(_image())

    assert parser.parsed_using_ocr
    assert md_doc.metadata["ocr"] == {
        "engine": "mistral",
        "model": "mistral-ocr-4-1",
        "pages": [0],
    }
    assert md_doc.to_string().startswith("# STATUTS\n")
    # the image is sent as an image, not wrapped in a pdf
    assert len(payloads) == 1
    assert _sent_image(payloads[0])[0] == "image/png"


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "L", "P", "CMYK"])
def test_parse_image(monkeypatch: pytest.MonkeyPatch, parser: ImageParser, mode: str):
    payloads = _mock_post(monkeypatch)
    md_doc = parser.parse_image(Image.new(mode, (600, 800)))

    assert md_doc.to_string().startswith("# STATUTS\n")
    assert len(payloads) == 1


def test_parse_multi_frame_image(monkeypatch: pytest.MonkeyPatch, parser: ImageParser):
    payloads = _mock_post(monkeypatch)
    image = Image.open(io.BytesIO(_tiff(frame_count=2)))
    md_doc = parser.parse_image(image)

    assert len(payloads) == 2
    assert md_doc.metadata["ocr"]["pages"] == [0, 1]


@pytest.mark.parametrize("extension", [".png", ".jpg", ".JPEG", ".tiff"])
def test_parse_file(
    monkeypatch: pytest.MonkeyPatch,
    parser: ImageParser,
    tmp_path: Path,
    extension: str,
):
    _mock_post(monkeypatch)
    images = {".png": _image("png"), ".jpg": _image("jpg"), ".jpeg": _image("jpg")}
    filepath = tmp_path / f"image{extension}"
    filepath.write_bytes(images.get(extension.lower()) or _tiff(frame_count=1))
    md_doc = parser.parse_file(str(filepath))

    assert parser.filepath == str(filepath)
    assert md_doc.to_string().startswith("# STATUTS\n")


def test_multi_frame_image_is_parsed_as_multi_page(
    monkeypatch: pytest.MonkeyPatch, parser: ImageParser
):
    payloads = _mock_post(monkeypatch)
    md_doc = parser.parse_string(_tiff(frame_count=2))

    # one request per frame
    assert len(payloads) == 2
    assert md_doc.metadata["ocr"]["pages"] == [0, 1]
    assert {block.page for block in parser.ocr_blocks} == {0, 1}


@pytest.mark.parametrize(
    ("image_format", "mime_type"), [("png", "image/png"), ("jpg", "image/jpeg")]
)
def test_image_format_is_kept(
    monkeypatch: pytest.MonkeyPatch,
    parser: ImageParser,
    image_format: str,
    mime_type: str,
):
    payloads = _mock_post(monkeypatch)
    parser.parse_string(_image(image_format))

    assert _sent_image(payloads[0])[0] == mime_type


@pytest.mark.parametrize(
    ("size", "sent_size"),
    [
        # small images are upscaled
        ((600, 800), (768, 1024)),
        ((60, 80), (768, 1024)),
        # bigger images are sent at their native resolution
        ((1500, 2000), (1500, 2000)),
        ((4000, 1800), (4000, 1800)),
        # huge images are downscaled
        ((6000, 3000), (4096, 2048)),
    ],
)
def test_image_resolution(
    monkeypatch: pytest.MonkeyPatch,
    parser: ImageParser,
    size: tuple[int, int],
    sent_size: tuple[int, int],
):
    payloads = _mock_post(monkeypatch)
    parser.parse_string(_image("png", *size))

    assert _sent_size(payloads[0]) == sent_size


def test_exif_orientation_is_applied(
    monkeypatch: pytest.MonkeyPatch, parser: ImageParser
):
    payloads = _mock_post(monkeypatch)
    image, buffer = Image.new("RGB", (1600, 1200)), io.BytesIO()
    exif = image.getexif()
    exif[0x0112] = 6  # orientation: rotate 90° clockwise to display
    image.save(buffer, format="JPEG", exif=exif)
    parser.parse_string(buffer.getvalue())

    assert _sent_size(payloads[0]) == (1200, 1600)


def test_orientation_classifier_turns_images_upright(
    monkeypatch: pytest.MonkeyPatch, parser: ImageParser
):
    payloads = _mock_post(monkeypatch)
    # as loaded by detect_orientation=True
    parser.orientation_classifier = _StubOrientationClassifier(90)  # type: ignore -> stub
    md_doc = parser.parse_string(_image("png", 1500, 2000))

    assert _sent_size(payloads[0]) == (2000, 1500)
    assert md_doc.metadata["ocr"]["rotations"] == {0: 90}


def test_image_without_text_raises(
    monkeypatch: pytest.MonkeyPatch, parser: ImageParser
):
    _mock_post(monkeypatch, empty=True)
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
