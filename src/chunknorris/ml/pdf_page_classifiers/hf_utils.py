"""HuggingFace download utilities for PDF page classifiers.

This module is imported lazily (after dependency checks pass), so the
top-level huggingface_hub imports are safe.
"""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError

# INT8 preferred over FP32 for both backends — faster and smaller.
_ONNX_INT8_FILES = ["model_int8.onnx", "config.json"]
_ONNX_FP32_FILES = ["model.onnx", "config.json"]

_OV_INT8_FILES = [
    "openvino_model_int8.xml",
    "openvino_model_int8.bin",
    "config.json",
]
_OV_FP32_FILES = ["openvino_model.xml", "openvino_model.bin", "config.json"]


def _download_from_hf(repo_id: str, filenames: list[str]) -> Path:
    """Download *filenames* from *repo_id* and return the local snapshot directory.

    Files land in the standard HuggingFace cache
    (``~/.cache/huggingface/hub/``).  The cache location can be overridden
    via the ``HF_HOME`` or ``HUGGINGFACE_HUB_CACHE`` environment variables.
    """
    last: Path | None = None
    for filename in filenames:
        last = Path(hf_hub_download(repo_id=repo_id, filename=filename))

    if last is None:
        raise ValueError("filenames must not be empty")
    return last.parent


def _download_with_int8_fallback(  # type: ignore[reportUnusedFunction]
    repo_id: str,
    int8_files: list[str],
    fp32_files: list[str],
) -> Path:
    """Download from HF, preferring INT8 over FP32 when available."""
    try:
        return _download_from_hf(repo_id, int8_files)
    except EntryNotFoundError:
        return _download_from_hf(repo_id, fp32_files)
