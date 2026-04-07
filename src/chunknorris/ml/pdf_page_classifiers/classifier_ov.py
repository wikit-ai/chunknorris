"""OpenVINO-based PDF page classifier for production inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

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
from .base_classifier import _BasePDFPageClassifier


class PDFPageClassifierOV(_BasePDFPageClassifier):
    """Classify PDF pages using a deployed OpenVINO IR model.

    Loads a self-contained deployment directory produced by
    ``export_onnx.save_for_deployment`` (with ``export_openvino=True``) and
    exposes the same ``predict`` interface as ``PDFPageClassifier``.

    Automatically selects the INT8 variant (``model_ov_int8.xml``) when it
    exists alongside the FP32 model, falling back to ``model_ov.xml``.

    Example::

        clf = PDFPageClassifierOV.from_pretrained("outputs/run-42/deployment")
        result = clf.predict("page_001.png")
        print(result.needs_image_embedding, result.predicted_classes)
    """

    def __init__(
        self,
        model_path: str,
        config: dict[str, Any],
        device: str = "CPU",
    ) -> None:
        """Initialise the classifier.

        Args:
            model_path: Path to the OpenVINO IR ``.xml`` file.
            config: Deployment config dict (same schema as config.json written
                by save_for_deployment).
            device: OpenVINO device string (``"CPU"``, ``"GPU"``, ``"AUTO"``).
        """
        super().__init__(config)
        compiled: CompiledModel = Core().compile_model(model_path, device)
        self._session: CompiledModel = compiled
        self._input_name: str = compiled.input(0).get_any_name()
        self._output = compiled.output(0)

    @property
    def backend(self) -> Literal["openvino"]:
        """Backend used for inference."""
        return "openvino"

    @classmethod
    def from_pretrained(
        cls,
        model_dir: str,
        device: str = "CPU",
    ) -> PDFPageClassifierOV:
        """Load a classifier from a deployment directory.

        The directory must contain:
          - ``model_ov.xml`` / ``model_ov_int8.xml`` — exported by
            save_for_deployment with ``export_openvino=True``
          - ``config.json`` — written by save_for_deployment

        The INT8 model (``model_ov_int8.xml``) is preferred when present.

        Args:
            model_dir: Path to the deployment directory.
            device: OpenVINO device string (``"CPU"``, ``"GPU"``, ``"AUTO"``).

        Returns:
            Initialised PDFPageClassifierOV.
        """
        path = Path(model_dir)
        config_path = path / "config.json"

        if not config_path.exists():
            raise FileNotFoundError(f"config.json not found in {model_dir}")

        # Search order: prefer INT8 over FP32, HF/Optimum names over legacy names
        candidates = [
            "openvino_model_int8.xml",  # HF-style INT8 (preferred)
            "openvino_model.xml",  # HF-style FP32
            "model_ov_int8.xml",  # legacy local INT8
            "model_ov.xml",  # legacy local FP32
        ]
        for candidate in candidates:
            if (path / candidate).exists():
                model_path = path / candidate
                break
        else:
            raise FileNotFoundError(
                f"No OpenVINO model found in {model_dir}. "
                f"Expected one of: {', '.join(candidates)}. "
                "Export with save_for_deployment(..., export_openvino=True)."
            )

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        instance = cls(str(model_path), config, device=device)
        instance._precision = "int8" if "int8" in model_path.name else "fp32"
        LOGGER.info("Loaded model : %s", instance.variant)

        return instance

    def _run_batch(
        self, batch_input: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        return self._session({self._input_name: batch_input})[self._output]
