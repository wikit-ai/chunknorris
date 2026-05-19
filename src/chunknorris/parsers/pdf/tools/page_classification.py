"""PDF page classification mixin.

Provides ML-based page classification as a composable mixin following the
same pattern as PdfTableExtraction, PdfLinkExtraction, etc.

Intended usage::

    parser = PdfParser(enable_ml_features=True)
    parser.parse_file("report.pdf")

    snapshots = list(parser.classify_pages())          # all parsed pages
    to_embed  = parser.get_images_of_pages_to_embed()  # generator of images needing embedding
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generator

from .components_ml import PdfPageSnapshot
from .utils import PdfParserState

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

    from ....ml.pdf_page_classifiers.classifier_onnx import PDFPageClassifierONNX
    from ....ml.pdf_page_classifiers.classifier_ov import PDFPageClassifierOV


class PdfPageClassification(PdfParserState):
    """Mixin that adds ML-based page classification to the PDF parser.

    Follows the same composition pattern as the other parser mixins: inherits
    from :class:`PdfParserState` for shared document state, and relies on
    :meth:`_render_page` provided by ``PdfPlotter`` being present in
    the final MRO (guaranteed when composed into ``PdfParser``).

    The classifier is loaded lazily when ``enable_ml_features=True`` is passed
    to :class:`PdfParser`.  If ML features are disabled, calling
    :meth:`classify_pages` raises a clear :exc:`RuntimeError` with install
    instructions rather than silently returning empty results.
    """

    _page_classifier: PDFPageClassifierOV | PDFPageClassifierONNX | None = None
    _ml_enabled: bool = False

    def _load_page_classifier(self) -> None:
        """Load the classifier using the global backend preference.

        Called once during ``PdfParser.__init__`` when
        ``enable_ml_features=True``.  Raises :exc:`ImportError` immediately if
        the required inference backend is not installed.
        """
        # pylint: disable=import-outside-toplevel
        from ....ml import get_ml_backend
        from ....ml.pdf_page_classifiers import load_classifier

        self._page_classifier = load_classifier(backend=get_ml_backend())

    def classify_pages(
        self,
        images: list[PILImage] | None = None,
        batch_size: int = 32,
        resolution: int = 100,
    ) -> Generator[PdfPageSnapshot, None, None]:
        """Classify parsed PDF pages and yield annotated snapshots one batch at a time.

        Pages are processed in batches of *batch_size* so that peak memory stays
        proportional to the batch rather than the full document.  When *images*
        is ``None``, pages are rendered on demand via :meth:`_render_page`
        (provided by ``PdfPlotter`` in the final MRO); images that do not need
        embedding are released after each batch.

        Args:
            images: Pre-rendered page images to classify.  When ``None``,
                pages are rendered automatically from the parsed document.
            batch_size: Pages rendered and classified per iteration.  Larger
                values trade memory for throughput.
            resolution: Rendering resolution in DPI (ignored when *images*
                is provided by the caller).

        Yields:
            :class:`PdfPageSnapshot` objects in page order.

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

        if images is not None:
            # Caller provided pre-rendered images — batch inference only.
            for batch_start in range(0, len(images), batch_size):
                batch_imgs = images[batch_start : batch_start + batch_size]
                preds = self._page_classifier.predict(batch_imgs, batch_size=len(batch_imgs))
                for j, (img, pred) in enumerate(zip(batch_imgs, preds)):  # type: ignore[arg-type]
                    yield PdfPageSnapshot(
                        page_number=self.page_start + batch_start + j,
                        image=img,
                        predictions=pred,  # type: ignore[arg-type]
                    )
        else:
            # Render and classify in batches — avoids loading all pages at once.
            end = self.page_end if self.page_end is not None else int(self.document.page_count)  # type: ignore[arg-type]
            page_indices = range(self.page_start, end)
            for batch_start in range(0, len(page_indices), batch_size):
                batch_range = page_indices[batch_start : batch_start + batch_size]
                batch_imgs = [self._render_page(n, resolution) for n in batch_range]  # type: ignore[attr-defined]
                preds = self._page_classifier.predict(batch_imgs, batch_size=len(batch_imgs))
                for n, img, pred in zip(batch_range, batch_imgs, preds):  # type: ignore[arg-type]
                    yield PdfPageSnapshot(
                        page_number=n,
                        image=img,
                        predictions=pred,  # type: ignore[arg-type]
                    )

    def get_images_of_pages_to_embed(
        self,
        batch_size: int = 32,
        resolution: int = 100,
    ) -> Generator[PILImage, None, None]:
        """Yield images of pages that require a visual (image) embedding.

        A thin filter over :meth:`classify_pages` that inherits its
        batch-at-a-time memory behaviour.

        Args:
            batch_size: Forwarded to :meth:`classify_pages`.
            resolution: Rendering resolution in DPI.

        Yields:
            PIL images for which ``needs_image_embedding`` is ``True``.

        Raises:
            RuntimeError: If ML features were not enabled at initialisation.
        """
        return (
            s.image
            for s in self.classify_pages(batch_size=batch_size, resolution=resolution)
            if s.needs_image_embedding
        )
