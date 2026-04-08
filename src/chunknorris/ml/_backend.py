"""Global ML backend configuration state for chunknorris."""

from __future__ import annotations

_preferred_backend: str = "auto"


def _is_installed(package: str) -> bool:
    """Return True if *package* can be imported without error."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


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


def set_ml_backend(backend: str) -> None:
    """Set the preferred ML inference backend for the entire library.

    Validates that the requested backend is installed before storing the
    preference.  Subsequent calls to ``load_classifier()`` (and
    ``PdfParser(enable_ml_features=True)``) will use this backend.

    Args:
        backend: ``"auto"`` (tries OpenVINO first, falls back to ONNX),
            ``"onnx"``, or ``"openvino"``.

    Raises:
        ValueError: If *backend* is not a recognised value.
        ImportError: If the required package for *backend* is not installed.

    Example::

        from chunknorris.ml import set_ml_backend
        set_ml_backend("openvino")
    """
    if backend not in ("auto", "onnx", "openvino"):
        raise ValueError(
            f"Unknown backend {backend!r}. Choose 'auto', 'onnx', or 'openvino'."
        )
    check_dependencies(backend)
    global _preferred_backend
    _preferred_backend = backend


def get_ml_backend() -> str:
    """Return the currently configured ML backend preference.

    Returns:
        One of ``"auto"``, ``"onnx"``, or ``"openvino"``.
    """
    return _preferred_backend
