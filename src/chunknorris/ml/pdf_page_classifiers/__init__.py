"""PDF page classifier — public factory with HuggingFace auto-download.

Local usage (directory with model files)::

    from chunknorris.ml.pdf_page_classifiers import load_classifier
    clf = load_classifier("path/to/model/dir")
    result = clf.predict("page.png")

HuggingFace usage (auto-download on first call, then cached)::

    from chunknorris.ml.pdf_page_classifiers import load_classifier
    clf = load_classifier()          # uses default Wikit repo
    result = clf.predict("page.png")
    print(result.needs_image_embedding, result.predicted_classes)

The downloaded model files are stored in the standard HuggingFace cache
(``~/.cache/huggingface/hub/``).  Set the ``HF_HOME`` or
``HUGGINGFACE_HUB_CACHE`` environment variable to customise the location.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Fixed HuggingFace repository — updated by Wikit when new model versions ship.
_DEFAULT_REPO_ID = "Wikit/pdf-pages-classifier"


# ---------------------------------------------------------------------------
# Dependency checking
# ---------------------------------------------------------------------------


def check_dependencies(backend: str = "auto") -> None:
    """Check that required ML packages are installed for *backend*.

    Args:
        backend: ``"auto"``, ``"onnx"``, or ``"openvino"``.

    Raises:
        ImportError: With a install hint if any package is missing.
    """
    missing: list[str] = []

    if not _is_installed("huggingface_hub"):
        missing.append("huggingface-hub  →  pip install huggingface-hub")

    has_onnx = _is_installed("onnxruntime")
    has_ov = _is_installed("openvino")

    if backend == "onnx" and not has_onnx:
        missing.append("onnxruntime  →  pip install onnxruntime")
    elif backend == "openvino" and not has_ov:
        missing.append("openvino  →  pip install openvino")
    elif backend == "auto" and not has_onnx and not has_ov:
        missing.append(
            "at least one inference backend:\n"
            "    onnxruntime  →  pip install onnxruntime\n"
            "    openvino     →  pip install openvino"
        )

    if missing:
        raise ImportError("Missing ML dependencies:\n  - " + "\n  - ".join(missing))


def _is_installed(package: str) -> bool:
    """Return True if *package* can be imported without error."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def _is_hf_repo_id(path: str) -> bool:
    """Return True if *path* looks like ``'owner/repo'`` rather than a local path."""
    if os.path.exists(path):
        return False
    normalized = path.replace("\\", "/")
    if normalized.startswith((".", "/", "~")):
        return False
    parts = normalized.split("/")
    return len(parts) == 2 and all(p.strip() for p in parts)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def load_classifier(
    repo_or_dir: str = _DEFAULT_REPO_ID,
    backend: str | None = None,
    device: str = "CPU",
) -> Any:
    """Load a PDF page classifier.

    Args:
        repo_or_dir: HuggingFace repo ID or local directory containing
            ``config.json`` and model files.  Defaults to the official Wikit
            repo (``"Wikit/pdf-pages-classifier"``).
        backend: ``"auto"`` tries OpenVINO first, falls back to ONNX.
            Pass ``"openvino"`` or ``"onnx"`` to force a specific backend.
            ``None`` defers to the library-wide preference set via
            :func:`chunknorris.ml.set_ml_backend` (default ``"auto"``).
        device: OpenVINO device string (``"CPU"``, ``"GPU"``, ``"AUTO"``).
            Ignored for the ONNX backend.

    Returns:
        A classifier instance exposing ``predict(images)``.

    Example::

        clf = load_classifier()
        result = clf.predict("page.png")
        print(result["needs_image_embedding"], result["predicted_classes"])
    """
    if backend is None:
        from chunknorris.ml import get_ml_backend

        backend = get_ml_backend()

    if backend not in ("auto", "onnx", "openvino"):
        raise ValueError(
            f"Unknown backend {backend!r}. Choose 'auto', 'onnx', or 'openvino'."
        )

    check_dependencies(backend)

    is_hf = _is_hf_repo_id(repo_or_dir)

    if backend in ("auto", "openvino"):
        try:
            return _load_openvino(repo_or_dir, device=device, is_hf=is_hf)
        except (ImportError, FileNotFoundError):
            if backend == "openvino":
                raise

    return _load_onnx(repo_or_dir, is_hf=is_hf)


# ---------------------------------------------------------------------------
# Backend-specific loaders
# ---------------------------------------------------------------------------


def _load_onnx(repo_or_dir: str, is_hf: bool) -> Any:
    from .classifier_onnx import PDFPageClassifierONNX
    from .hf_utils import (
        _ONNX_FP32_FILES,
        _ONNX_INT8_FILES,
        _download_with_int8_fallback,
    )

    model_dir = (
        _download_with_int8_fallback(repo_or_dir, _ONNX_INT8_FILES, _ONNX_FP32_FILES)
        if is_hf
        else Path(repo_or_dir)
    )
    return PDFPageClassifierONNX.from_pretrained(str(model_dir))


def _load_openvino(repo_or_dir: str, device: str, is_hf: bool) -> Any:
    from .classifier_ov import PDFPageClassifierOV
    from .hf_utils import _OV_FP32_FILES, _OV_INT8_FILES, _download_with_int8_fallback

    model_dir = (
        _download_with_int8_fallback(repo_or_dir, _OV_INT8_FILES, _OV_FP32_FILES)
        if is_hf
        else Path(repo_or_dir)
    )
    return PDFPageClassifierOV.from_pretrained(str(model_dir), device=device)
