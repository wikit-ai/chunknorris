"""ML utilities for chunknorris — global backend configuration.

Usage::

    from chunknorris.ml import set_ml_backend
    set_ml_backend("openvino")   # validated + dependency-checked immediately
"""

from ._backend import get_ml_backend, set_ml_backend

__all__ = ["get_ml_backend", "set_ml_backend"]
