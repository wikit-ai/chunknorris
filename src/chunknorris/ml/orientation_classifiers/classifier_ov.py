"""OpenVINO document orientation classifier."""

from __future__ import annotations

from typing import Literal

import numpy as np
import numpy.typing as npt

try:
    from openvino import CompiledModel, Core
except ImportError as _e:
    raise ImportError(
        "openvino is required for OpenVINO inference.\n"
        "Install with: pip install openvino"
    ) from _e

from ...core.logger import LOGGER
from .base_classifier import _BaseOrientationClassifier


class OrientationClassifierOV(_BaseOrientationClassifier):
    """Predicts the orientation of document images using OpenVINO.
    OpenVINO reads the ONNX model directly, no conversion is needed.

    Example::

        clf = OrientationClassifierOV("path/to/inference.onnx")
        prediction = clf.predict("page.png")
        print(prediction.angle, prediction.confidence)
    """

    def __init__(
        self, model_path: str, min_confidence: float = 0.7, device: str = "CPU"
    ) -> None:
        """Initialise the classifier.

        Args:
            model_path: Path to the ONNX model file.
            min_confidence: see :class:`_BaseOrientationClassifier`.
            device: OpenVINO device string (``"CPU"``, ``"GPU"``, ``"AUTO"``).
        """
        super().__init__(min_confidence)
        compiled: CompiledModel = Core().compile_model(model_path, device)  # type: ignore
        self._session: CompiledModel = compiled
        self._input_name: str = compiled.input(0).get_any_name()  # type: ignore
        self._output = compiled.output(0)  # type: ignore
        LOGGER.info("Loaded model : %s", self.variant)

    @property
    def backend(self) -> Literal["openvino"]:
        """Backend used for inference."""
        return "openvino"

    def _run_batch(
        self, batch_input: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        return self._session({self._input_name: batch_input})[self._output]  # type: ignore
