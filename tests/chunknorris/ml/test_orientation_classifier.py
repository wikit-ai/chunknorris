from concurrent.futures import ThreadPoolExecutor

import pymupdf  # type: ignore -> no stubs
import pytest
from PIL import Image

from chunknorris.ml.orientation_classifiers import (
    OrientationPrediction,
    load_orientation_classifier,
)

try:
    import onnxruntime  # type: ignore # pylint: disable=unused-import

    ONNX_AVAILABLE = True
except ImportError:  # the ml-onnx extra is not installed
    ONNX_AVAILABLE = False

try:
    import openvino  # type: ignore # pylint: disable=unused-import

    OPENVINO_AVAILABLE = True
except ImportError:  # the ml-openvino extra is not installed
    OPENVINO_AVAILABLE = False


@pytest.mark.skipif(not ONNX_AVAILABLE, reason="requires the ml-onnx extra")
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_predicts_page_rotation(pdf_filepath: str, rotation: int):
    classifier = load_orientation_classifier(backend="onnx")
    page = pymupdf.open(pdf_filepath)[0]
    page.set_rotation(rotation)  # type: ignore -> missing typing
    pixmap = page.get_pixmap(dpi=72, alpha=False)  # type: ignore -> missing typing
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)  # type: ignore -> missing typing

    prediction = classifier.predict(image)

    assert isinstance(prediction, OrientationPrediction)
    assert prediction.angle == rotation
    assert prediction.is_confident


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param(
            "onnx",
            marks=pytest.mark.skipif(
                not ONNX_AVAILABLE, reason="requires the ml-onnx extra"
            ),
        ),
        pytest.param(
            "openvino",
            marks=pytest.mark.skipif(
                not OPENVINO_AVAILABLE, reason="requires the ml-openvino extra"
            ),
        ),
    ],
)
def test_predicts_concurrently(backend: str):
    """The classifier is shared between parsers, that may run in several threads."""
    classifier = load_orientation_classifier(backend=backend)
    images = [Image.new("RGB", (600, 800), "white")] * 4

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: classifier.predict(images), range(32)))

    assert all(len(predictions) == 4 for predictions in results)  # type: ignore -> predict() returns a list when given a list


def test_rejects_unknown_backend():
    with pytest.raises(ValueError, match="Unknown backend"):
        load_orientation_classifier(backend="tensorflow")
