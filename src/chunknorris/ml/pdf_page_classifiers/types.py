from pydantic import BaseModel


class PdfPagePrediction(BaseModel):
    needs_image_embedding: bool
    predicted_classes: list[str]
    probabilities: dict[str, float]
