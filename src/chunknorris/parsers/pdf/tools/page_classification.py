"""PDF page classification mixin.

Provides ML-based page classification as a composable mixin following the
same pattern as PdfTableExtraction, PdfLinkExtraction, etc.

Intended usage::

    parser = PdfParser(enable_ml_features=True)
    parser.parse_file("report.pdf")

    snapshots = parser.classify_pages()          # all parsed pages
    to_embed  = parser.get_pages_to_embed()      # pages needing image embedding
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....decorators.decorators import timeit

from .components_ml import PdfPageSnapshot
from .utils import PdfParserState

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


class PdfPageClassification(PdfParserState):
    """Mixin that adds ML-based page classification to the PDF parser.

    Follows the same composition pattern as the other parser mixins: inherits
    from :class:`PdfParserState` for shared document state, and relies on
    :meth:`get_pages_as_images` provided by ``PdfPlotter`` being present in
    the final MRO (guaranteed when composed into ``PdfParser``).

    The classifier is loaded lazily when ``enable_ml_features=True`` is passed
    to :class:`PdfParser`.  If ML features are disabled, calling
    :meth:`classify_pages` raises a clear :exc:`RuntimeError` with install
    instructions rather than silently returning empty results.
    """

    _page_classifier: Any | None = None
    _ml_enabled: bool = False

    def _load_page_classifier(self) -> None:
        """Load the classifier using the global backend preference.

        Called once during ``PdfParser.__init__`` when
        ``enable_ml_features=True``.  Raises :exc:`ImportError` immediately if
        the required inference backend is not installed.
        """
        from ....ml import get_ml_backend
        from ....ml.pdf_page_classifiers import load_classifier

        self._page_classifier = load_classifier(backend=get_ml_backend())

    @timeit
    def classify_pages(
        self,
        images: list[PILImage] | None = None,
        batch_size: int = 32,
    ) -> list[PdfPageSnapshot]:
        """Classify all parsed PDF pages and return annotated snapshots.

        On the first call without *images*, pages are rendered and stored in
        ``self._page_images``.  The snapshots reference those cached objects
        directly, so no image data is duplicated in memory.

        Args:
            images: Pre-rendered page images to classify.  When ``None``,
                :meth:`get_pages_as_images` is called automatically to render
                and cache all pages in the parsed range.
            batch_size: Number of images per inference batch passed to the
                classifier.  Increase for faster throughput on GPU; decrease
                to reduce peak memory.

        Returns:
            A list of :class:`PdfPageSnapshot` objects, one per page, in
            page order.

        Raises:
            RuntimeError: If ML features were not enabled at initialisation.
        """
        if not self._ml_enabled or self._page_classifier is None:
            raise RuntimeError(
                "ML features are disabled.\n"
                "Initialise the parser with: PdfParser(enable_ml_features=True)\n"
                "Required packages: pip install chunknorris[ml-onnx]  "
                "or  pip install chunknorris[ml-openvino]"
            )

        if images is None:
            images = self.get_pages_as_images()  # type: ignore[attr-defined]  # provided by PdfPlotter

        predictions: list[dict[str, Any]] = self._page_classifier.predict(
            images, batch_size=batch_size
        )

        return [
            PdfPageSnapshot(
                page_number=self.page_start + i,  # offset if page_start != 0
                image=img,
                predictions=pred,
            )
            for i, (img, pred) in enumerate(zip(images, predictions))
        ]

    def get_images_of_pages_to_embed(self) -> list[PdfPageSnapshot]:
        """Return only the images of the pages that require a visual (image) embedding.

        Returns:
            Filtered list of :class:`PdfPageSnapshot` where
            ``needs_image_embedding`` is ``True``.

        Raises:
            RuntimeError: If ML features were not enabled at initialisation.
        """
        return [s.image for s in self.classify_pages() if s.needs_image_embedding]
