"""ML utilities for chunknorris — global backend configuration.

Usage::

    from chunknorris.ml import set_ml_backend
    set_ml_backend("openvino")   # validated + dependency-checked immediately
"""

from __future__ import annotations

_preferred_backend: str = "auto"


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
    from .pdf_page_classifiers import check_dependencies

    check_dependencies(backend)
    global _preferred_backend
    _preferred_backend = backend


def get_ml_backend() -> str:
    """Return the currently configured ML backend preference.

    Returns:
        One of ``"auto"``, ``"onnx"``, or ``"openvino"``.
    """
    return _preferred_backend
