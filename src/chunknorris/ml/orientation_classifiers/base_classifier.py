from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
import numpy.typing as npt
from PIL import Image

from .types import OrientationPrediction


def _resize_linear(
    arr: npt.NDArray[np.float32], width: int, height: int
) -> npt.NDArray[np.float32]:
    """Bilinear resize without antialiasing, as cv2.resize(interpolation=INTER_LINEAR)
    used to train the model. PIL's bilinear antialiases when downscaling, which blurs
    the text and makes the model notably less accurate.

    Args:
        arr: (H, W, C) image array.
        width: target width.
        height: target height.

    Returns:
        (height, width, C) resized array.
    """

    def sample_points(size_out: int, size_in: int):  # type: ignore[no-untyped-def]
        # half-pixel centers, each output pixel interpolates its 2 nearest input pixels
        x = (np.arange(size_out) + 0.5) * (size_in / size_out) - 0.5
        x = np.clip(x, 0, size_in - 1)
        x0 = np.floor(x).astype(int)
        x1 = np.minimum(x0 + 1, size_in - 1)
        return x0, x1, (x - x0).astype(np.float32)

    y0, y1, fy = sample_points(height, arr.shape[0])
    x0, x1, fx = sample_points(width, arr.shape[1])
    fx, fy = fx[None, :, None], fy[:, None, None]
    top = arr[y0][:, x0] * (1 - fx) + arr[y0][:, x1] * fx
    bottom = arr[y1][:, x0] * (1 - fx) + arr[y1][:, x1] * fx

    return top * (1 - fy) + bottom * fy


class _BaseOrientationClassifier(ABC):  # type: ignore[reportUnusedClass]
    """Shared preprocessing, formatting, and predict logic of the
    PP-LCNet_x1_0_doc_ori document orientation classifier.

    Subclasses must implement ``_run_batch`` to perform backend-specific
    inference on a (N, C, H, W) float32 numpy array.
    """

    # Preprocessing of the model, as defined in its inference.yml
    _RESIZE_SHORT: int = 256
    _CROP_SIZE: int = 224
    _MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    _STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    _ANGLES: tuple[int, ...] = (0, 90, 180, 270)

    def __init__(self, min_confidence: float = 0.7) -> None:
        """Initialise the classifier.

        Args:
            min_confidence: probability under which a prediction is flagged as
                not confident. The model rarely goes above 0.94.
        """
        self.min_confidence = min_confidence

    @property
    @abstractmethod
    def backend(self) -> Literal["onnx", "openvino"]:
        """Backend used for inference."""

    @property
    def variant(self) -> str:
        """Human-readable variant string, e.g. ``'Document orientation classifier, onnx'``."""
        return f"Document orientation classifier, {self.backend}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(variant={self.variant!r}, min_confidence={self.min_confidence})"

    @abstractmethod
    def _run_batch(
        self, batch_input: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Run inference on a (N, C, H, W) float32 batch.

        Returns:
            (N, 4) float32 array of probabilities.
        """

    def _preprocess(self, image: str | Image.Image) -> npt.NDArray[np.float32]:
        """Resizes the shortest side, center crops and normalizes the image.

        Args:
            image: File path or PIL image (any mode).

        Returns:
            Float32 array of shape (C, H, W).
        """
        img = (
            Image.open(image).convert("RGB")
            if isinstance(image, str)
            else image.convert("RGB")
        )
        w, h = img.size
        scale = self._RESIZE_SHORT / min(w, h)
        arr = _resize_linear(
            np.asarray(img, dtype=np.float32), round(w * scale), round(h * scale)
        )
        h, w = arr.shape[:2]
        left, top = (w - self._CROP_SIZE) // 2, (h - self._CROP_SIZE) // 2
        arr = arr[top : top + self._CROP_SIZE, left : left + self._CROP_SIZE]
        arr = arr * (1.0 / 255.0)
        arr = (arr - self._MEAN) / self._STD

        return arr.transpose(2, 0, 1)

    def _format(self, probabilities: npt.NDArray[np.float32]) -> OrientationPrediction:
        best = int(probabilities.argmax())
        confidence = float(probabilities[best])
        return OrientationPrediction(
            angle=self._ANGLES[best],
            confidence=confidence,
            is_confident=confidence >= self.min_confidence,
            probabilities={
                angle: float(prob) for angle, prob in zip(self._ANGLES, probabilities)
            },
        )

    def predict(
        self,
        images: str | Image.Image | list[str | Image.Image],
        batch_size: int = 32,
    ) -> OrientationPrediction | list[OrientationPrediction]:
        """Predicts the orientation of one or more page images.

        Args:
            images: A single image (file path or PIL image) or a list of images.
            batch_size: Number of images to process per inference call.

        Returns:
            A single ``OrientationPrediction`` when ``images`` is not a list,
            or a list of ``OrientationPrediction`` otherwise.
        """
        is_single = not isinstance(images, list)
        image_list: list[str | Image.Image] = [images] if is_single else images  # type: ignore[list-item]

        predictions: list[OrientationPrediction] = []
        for batch_start in range(0, len(image_list), batch_size):
            batch = image_list[batch_start : batch_start + batch_size]
            batch_input = np.stack([self._preprocess(image) for image in batch])
            predictions.extend(
                self._format(probs) for probs in self._run_batch(batch_input)
            )

        return predictions[0] if is_single else predictions

    def __call__(
        self,
        images: str | Image.Image | list[str | Image.Image],
        batch_size: int = 32,
    ) -> OrientationPrediction | list[OrientationPrediction]:
        """Delegate to predict(). See predict() for full documentation."""
        return self.predict(images, batch_size=batch_size)
