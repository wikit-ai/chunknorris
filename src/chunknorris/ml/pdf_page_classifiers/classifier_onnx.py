"""PDF page classifier for production inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import numpy as np
import numpy.typing as npt

from ...core.logger import LOGGER
from .base_classifier import _BasePDFPageClassifier

try:
    import onnxruntime as ort
except ImportError as _e:
    raise ImportError(
        "onnxruntime is required for inference.\n"
        "Install with: pip install onnxruntime"
    ) from _e


class PDFPageClassifierONNX(_BasePDFPageClassifier):
    """Classify PDF pages using a deployed ONNX model.

    Loads a self-contained deployment directory produced by
    ``export_onnx.save_for_deployment`` and exposes a simple ``predict``
    interface.  All preprocessing (center-crop, resize, normalization) is
    performed in pure PIL + numpy, matching the pipeline used during training.

    Example::

        clf = PDFPageClassifier.from_pretrained("outputs/run-42/deployment")
        result = clf.predict("page_001.png")
        print(result.needs_image_embedding, result.predicted_classes)
    """

    def __init__(self, model_path: str, config: dict[str, Any]) -> None:
        """Initialise the classifier.

        Args:
            model_path: Path to the ONNX model file.
            config: Deployment config dict (same schema as config.json written
                by save_for_deployment).
        """
        super().__init__(config)
        self._session = ort.InferenceSession(model_path)  # type: ignore[unknownMemberType]
        self._input_name: str = self._session.get_inputs()[0].name  # type: ignore[unknownMemberType]

    @property
    def backend(self) -> Literal["onnx"]:
        """Backend used for inference."""
        return "onnx"

    @classmethod
    def from_pretrained(cls, model_dir: str) -> PDFPageClassifierONNX:
        """Load a classifier from a deployment directory.

        The directory must contain:
          - ``model.onnx``
          - ``config.json``

        Args:
            model_dir: Path to the deployment directory.

        Returns:
            Initialised PDFPageClassifier.
        """
        path = Path(model_dir)
        config_path = path / "config.json"

        if not config_path.exists():
            raise FileNotFoundError(f"config.json not found in {model_dir}")

        # Prefer INT8 (QAT export) over FP32 when both are present
        candidates = ["model_int8.onnx", "model.onnx"]
        for candidate in candidates:
            if (path / candidate).exists():
                model_path = path / candidate
                break
        else:
            raise FileNotFoundError(
                f"No ONNX model found in {model_dir}. "
                f"Expected one of: {', '.join(candidates)}."
            )

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        instance = cls(str(model_path), config)
        instance._precision = "int8" if "int8" in model_path.name else "fp32"
        LOGGER.info("Loaded model : %s", instance.variant)

        return instance

    def _run_batch(
        self, batch_input: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        return self._session.run(None, {self._input_name: batch_input})[0]  # type: ignore[unknownMemberType]
