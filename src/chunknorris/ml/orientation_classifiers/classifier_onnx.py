"""ONNX Runtime document orientation classifier."""

from __future__ import annotations

from typing import Literal

import numpy as np
import numpy.typing as npt

from ...core.logger import LOGGER
from .base_classifier import _BaseOrientationClassifier

try:
    import onnxruntime as ort
except ImportError as _e:
    raise ImportError(
        "onnxruntime is required for inference.\n"
        "Install with: pip install onnxruntime"
    ) from _e


class OrientationClassifierONNX(_BaseOrientationClassifier):
    """Predicts the orientation of document images using ONNX Runtime.

    Example::

        clf = OrientationClassifierONNX("path/to/inference.onnx")
        prediction = clf.predict("page.png")
        print(prediction.angle, prediction.confidence)
    """

    def __init__(self, model_path: str, min_confidence: float = 0.7) -> None:
        """Initialise the classifier.

        Args:
            model_path: Path to the ONNX model file.
            min_confidence: see :class:`_BaseOrientationClassifier`.
        """
        super().__init__(min_confidence)
        self._session = ort.InferenceSession(model_path)  # type: ignore[unknownMemberType]
        self._input_name: str = self._session.get_inputs()[0].name  # type: ignore[unknownMemberType]
        LOGGER.info("Loaded model : %s", self.variant)

    @property
    def backend(self) -> Literal["onnx"]:
        """Backend used for inference."""
        return "onnx"

    def _run_batch(
        self, batch_input: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        return self._session.run(None, {self._input_name: batch_input})[0]  # type: ignore[unknownMemberType]
