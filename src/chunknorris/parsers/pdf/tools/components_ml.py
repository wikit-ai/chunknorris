"""ML-related components for the PDF parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ....ml.pdf_page_classifiers.types import PdfPagePrediction

if TYPE_CHECKING:
    from PIL import Image


@dataclass
class PdfPageSnapshot:
    """A rendered snapshot of a single PDF page, optionally annotated with
    classifier predictions.

    Images are stored by reference — they point to the same ``PIL.Image``
    objects cached in ``PdfParser._page_images``, so holding a list of
    snapshots does not duplicate memory.

    Attributes:
        page_number: Zero-based page index within the source document.
        image: The rendered PIL image for this page.
        predictions: Raw output dict from the page classifier, or ``None``
            if :meth:`PdfParser.classify_pages` has not been called yet.
    """

    page_number: int
    image: Image.Image
    predictions: PdfPagePrediction | None = None

    @property
    def needs_image_embedding(self) -> bool:
        """Whether this page requires a visual (image) embedding.

        Raises:
            RuntimeError: If predictions have not been computed yet.
        """
        if self.predictions is None:
            raise RuntimeError(
                "Predictions not computed yet. Call classify_pages() first."
            )
        return bool(self.predictions.needs_image_embedding)

    @property
    def predicted_classes(self) -> list[str]:
        """List of predicted class labels for this page.

        Raises:
            RuntimeError: If predictions have not been computed yet.
        """
        if self.predictions is None:
            raise RuntimeError(
                "Predictions not computed yet. Call classify_pages() first."
            )
        return list(self.predictions.predicted_classes)
