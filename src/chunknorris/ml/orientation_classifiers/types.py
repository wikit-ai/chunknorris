from pydantic import BaseModel


class OrientationPrediction(BaseModel):
    """Orientation predicted for a page image.

    Attributes:
        angle: clockwise rotation (0, 90, 180 or 270) of the content of the image.
            To make the image upright, rotate it counterclockwise by this angle.
            For a pymupdf page: ``page.set_rotation((page.rotation - angle) % 360)``.
        confidence: probability of the predicted angle.
        is_confident: whether the confidence reaches the classifier's ``min_confidence``.
        probabilities: probability of each angle.
    """

    angle: int
    confidence: float
    is_confident: bool
    probabilities: dict[int, float]
