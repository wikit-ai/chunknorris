"""Document orientation classifier — public factory with HuggingFace auto-download.

Predicts whether a page image is rotated by 0, 90, 180 or 270 degrees, using
PaddlePaddle's PP-LCNet_x1_0_doc_ori model.

Usage::

    from chunknorris.ml.orientation_classifiers import load_orientation_classifier
    clf = load_orientation_classifier()   # downloads the model on first call
    prediction = clf.predict("page.png")
    print(prediction.angle, prediction.confidence)

The downloaded model files are stored in the standard HuggingFace cache
(``~/.cache/huggingface/hub/``).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from chunknorris.ml._backend import check_dependencies, get_ml_backend

from .types import OrientationPrediction

if TYPE_CHECKING:
    from .classifier_onnx import OrientationClassifierONNX
    from .classifier_ov import OrientationClassifierOV

    OrientationClassifier = OrientationClassifierONNX | OrientationClassifierOV

_DEFAULT_REPO_ID = "PaddlePaddle/PP-LCNet_x1_0_doc_ori_onnx"
_MODEL_FILENAME = "inference.onnx"

__all__ = ["OrientationPrediction", "load_orientation_classifier"]


def load_orientation_classifier(
    repo_or_path: str = _DEFAULT_REPO_ID,
    min_confidence: float = 0.7,
    backend: str | None = None,
    device: str = "CPU",
) -> OrientationClassifier:
    """Load a document orientation classifier.

    Args:
        repo_or_path: HuggingFace repo ID holding ``inference.onnx``, or path to
            a local ONNX file. Defaults to ``"PaddlePaddle/PP-LCNet_x1_0_doc_ori_onnx"``.
        min_confidence: probability under which a prediction is flagged as not
            confident (``prediction.is_confident``). Defaults to 0.7.
        backend: ``"auto"`` tries OpenVINO first, falls back to ONNX.
            Pass ``"openvino"`` or ``"onnx"`` to force a specific backend.
            ``None`` defers to the library-wide preference set via
            :func:`chunknorris.ml.set_ml_backend` (default ``"auto"``).
        device: OpenVINO device string (``"CPU"``, ``"GPU"``, ``"AUTO"``).
            Ignored for the ONNX backend.

    Returns:
        A classifier instance exposing ``predict(images)``. It is loaded once and
        shared by all the calls made with the same arguments.
    """
    if backend is None:
        backend = get_ml_backend()

    if backend not in ("auto", "onnx", "openvino"):
        raise ValueError(
            f"Unknown backend {backend!r}. Choose 'auto', 'onnx', or 'openvino'."
        )

    check_dependencies(backend)

    return _load(repo_or_path, min_confidence, backend, device)


@cache
def _load(
    repo_or_path: str, min_confidence: float, backend: str, device: str
) -> OrientationClassifier:
    if Path(repo_or_path).is_file():
        model_path = repo_or_path
    else:
        from ..pdf_page_classifiers.hf_utils import (  # pylint: disable=import-outside-toplevel
            _download_from_hf,
        )

        model_path = str(
            _download_from_hf(repo_or_path, [_MODEL_FILENAME]) / _MODEL_FILENAME
        )

    if backend in ("auto", "openvino"):
        try:
            # pylint: disable=import-outside-toplevel
            from .classifier_ov import OrientationClassifierOV

            return OrientationClassifierOV(model_path, min_confidence, device=device)
        except ImportError:
            if backend == "openvino":
                raise

    # pylint: disable=import-outside-toplevel
    from .classifier_onnx import OrientationClassifierONNX

    return OrientationClassifierONNX(model_path, min_confidence)
