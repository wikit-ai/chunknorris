from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
from PIL import Image

from .types import PdfPagePrediction


class _BasePDFPageClassifier(ABC):  # type: ignore[reportUnusedClass]
    """Shared preprocessing, formatting, and predict logic.

    Subclasses must implement ``_run_batch`` to perform backend-specific
    inference on a (N, C, H, W) float32 numpy array.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._image_size: int = config["image_size"]
        self._mean = np.array(config["mean"], dtype=np.float32)
        self._std = np.array(config["std"], dtype=np.float32)
        self._center_crop: bool = config.get("center_crop_shortest", True)
        self._whiteout: bool = config.get("whiteout_header", False)
        self._whiteout_cutoff: int = int(
            self._image_size * config.get("whiteout_fraction", 0.15)
        )
        self._class_names: list[str] = config["class_names"]
        self._threshold: float = float(config.get("threshold", 0.5))
        self._image_required_classes: set[str] = set(
            config.get("image_required_classes", [])
        )
        self._precision: str = ""

    @property
    @abstractmethod
    def backend(self) -> Literal["onnx", "openvino"]:
        """Backend used for inference."""

    @property
    def friendly_name(self) -> str:
        return "PDF pages classifier"

    @property
    def precision(self) -> Literal["int8", "fp32"]:
        """Precision of the loaded model."""
        return self._precision

    @property
    def variant(self) -> str:
        """Human-readable variant string, e.g. ``'onnx/int8'`` or ``'openvino/fp32'``."""
        return f"{self.friendly_name}, {self.backend}/{self.precision}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(variant={self.variant!r})"

    @abstractmethod
    def _run_batch(
        self, batch_input: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Run inference on a (N, C, H, W) float32 batch.

        Returns:
            (N, num_classes) float32 array of probabilities.
        """

    @staticmethod
    def _load_image(item: str | Image.Image) -> Image.Image:
        """Load an image from a file path or PIL image and convert to RGB.

        Args:
            item: File path string or PIL image (any mode).

        Returns:
            RGB PIL image.

        Raises:
            TypeError: If ``item`` is neither a str nor a PIL.Image.
        """
        if isinstance(item, str):
            return Image.open(item).convert("RGB")
        return item.convert("RGB")

    def _pil_to_array(self, img: Image.Image) -> npt.NDArray[np.float32]:
        """Apply spatial transforms and return a (H, W, C) float32 array in [0, 1].

        Normalization and the channel transpose are intentionally deferred so
        they can be applied in a single vectorised pass over the whole batch in
        ``_normalize_batch``.

        Steps:
          1. Center-crop to square (shortest side), if enabled.
          2. Resize to (image_size, image_size) with bicubic interpolation.
          3. Scale pixel values to [0, 1].
          4. White out top header rows, if enabled.

        Args:
            img: RGB PIL image.

        Returns:
            Float32 array of shape (image_size, image_size, 3).
        """
        if self._center_crop:
            w, h = img.size
            sq = min(w, h)
            img = img.crop(((w - sq) // 2, (h - sq) // 2, (w + sq) // 2, (h + sq) // 2))

        img = img.resize((self._image_size, self._image_size), Image.Resampling.BICUBIC)
        arr = np.asarray(img, dtype=np.float32) * (1.0 / 255.0)  # (H, W, C)

        if self._whiteout:
            arr[: self._whiteout_cutoff] = 1.0

        return arr

    def _normalize_batch(
        self, arrays: list[npt.NDArray[np.float32]]
    ) -> npt.NDArray[np.float32]:
        """Stack a list of (H, W, C) arrays and apply ImageNet normalization.

        Args:
            arrays: List of float32 arrays, each of shape (H, W, C) in [0, 1].

        Returns:
            Float32 array of shape (N, C, H, W), normalized with ImageNet stats.
        """
        batch = np.stack(arrays, axis=0)  # (N, H, W, C)
        batch = (batch - self._mean) / self._std  # broadcast over (H, W, C)
        return batch.transpose(0, 3, 1, 2)  # (N, C, H, W)

    def _format(
        self,
        probabilities: npt.NDArray[np.float32],
        threshold: float,
    ) -> PdfPagePrediction:
        """Format model output probabilities into a prediction object.

        Args:
            probabilities: 1-D float32 array of per-class probabilities.
            threshold: Probability cutoff for a positive prediction.

        Returns:
            A ``PdfPagePrediction`` instance.
        """
        predicted_classes = [
            name
            for name, prob in zip(self._class_names, probabilities)
            if prob >= threshold
        ]
        return PdfPagePrediction(
            needs_image_embedding=any(
                c in self._image_required_classes for c in predicted_classes
            ),
            predicted_classes=predicted_classes,
            probabilities={
                name: float(prob)
                for name, prob in zip(self._class_names, probabilities)
            },
        )

    def predict(
        self,
        images: str | Image.Image | list[Any],
        threshold: float | None = None,
        batch_size: int = 32,
        num_workers: int = 4,
    ) -> PdfPagePrediction | list[PdfPagePrediction]:
        """Classify one or more PDF page images.

        Args:
            images: A single image (file path string or PIL.Image) or a list
                of images.
            threshold: Override the default probability threshold from config.
                The override is local to this call and does not mutate the
                classifier instance.
            batch_size: Number of images to process per inference call.
            num_workers: Number of threads for parallel image loading and
                preprocessing. Set to 1 to disable threading.

        Returns:
            A single ``PdfPagePrediction`` when ``images`` is not a list, or a
            list of ``PdfPagePrediction`` otherwise.
        """
        effective_threshold = self._threshold if threshold is None else threshold

        is_single = not isinstance(images, list)
        image_list: list[Any] = [images] if is_single else images

        all_results: list[PdfPagePrediction] = []

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            for batch_start in range(0, len(image_list), batch_size):
                batch_items = image_list[batch_start : batch_start + batch_size]

                # Load (file I/O + RGB conversion) in parallel, then free after use.
                loaded: list[Image.Image] = list(
                    executor.map(self._load_image, batch_items)
                )
                # PIL transforms (crop + bicubic resize) in parallel.
                arrays: list[npt.NDArray[np.float32]] = list(
                    executor.map(self._pil_to_array, loaded)
                )

                # Vectorised normalization + transpose, then inference.
                batch_input = self._normalize_batch(arrays)  # (N, C, H, W)
                probs_batch: npt.NDArray[np.float32] = self._run_batch(batch_input)

                all_results.extend(
                    self._format(probs, effective_threshold) for probs in probs_batch
                )

        return all_results[0] if is_single else all_results

    def __call__(
        self,
        images: str | Image.Image | list[Any],
        threshold: float | None = None,
        batch_size: int = 32,
        num_workers: int = 4,
    ) -> PdfPagePrediction | list[PdfPagePrediction]:
        """Delegate to predict(). See predict() for full documentation."""
        return self.predict(
            images, threshold=threshold, batch_size=batch_size, num_workers=num_workers
        )
