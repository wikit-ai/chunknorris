import base64
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any

import pymupdf  # type: ignore : no stubs

from ...exceptions.exceptions import PdfParserException
from .base import DocumentOCREngine
from .types import OCRBlock, OCRDocument, OCRImage

IMAGE_TYPES = [
    "chart",
    "table",
    "flowchart",
    "diagram",
    "infographic",
    "screenshot",
    "photo",
    "technical_drawing",
    "map",
    "equation",
    "text_block",
    "signature",
    "stamp",
    "logo",
    "qr_code",
    "icon",
    "decorative",
    "other",
]

IMAGE_ANNOTATION_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "image_annotation",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["image_type", "caption"],
            "properties": {
                "image_type": {
                    "type": "string",
                    "enum": IMAGE_TYPES,
                    "description": (
                        "Category of the image. Pick the single most specific one. "
                        "chart: quantitative plot (bar, line, pie, scatter, area, gauge). "
                        "table: a table rendered as an image. "
                        "flowchart: process or workflow with ordered steps and decisions. "
                        "diagram: structure of components and their relations (architecture, network, org chart, tree, mind map, timeline). "
                        "infographic: mix of pictograms, key figures and short texts conveying messages. "
                        "screenshot: capture of a software, website, mobile app or terminal interface. "
                        "photo: real-world photograph that carries information (product, equipment, site, damage, person in context). "
                        "technical_drawing: plan, blueprint, schematic, exploded view or labeled illustration of an object. "
                        "map: geographic map or floor plan. "
                        "equation: mathematical or chemical formula. "
                        "text_block: image whose content is mainly text (scanned paragraph, callout, handwritten note, banner title). "
                        "signature: handwritten signature or initials. A handwritten scrawl is a signature even when it reads like a name or a brand. "
                        "stamp: stamp or seal, usually inked, round or rectangular. "
                        "logo: printed brand or organization mark, never handwritten. "
                        "qr_code: QR code or barcode. "
                        "icon: small pictogram or UI icon. "
                        "decorative: no informational value (background, separator, frame, generic stock photo or illustration). "
                        "other: none of the above."
                    ),
                },
                "caption": {
                    "type": "string",
                    "description": (
                        "Text replacement of the image for a retrieval (RAG) system that cannot see it: "
                        "someone reading only the caption must get all the information the image conveys. "
                        "Use only what is visible in the image and never invent values, names or links. "
                        "Write in the language of the text visible in the image, or in French if there is no text. "
                        "Copy visible labels, numbers and names exactly. "
                        "Start directly with the content, without preamble such as 'This image shows', "
                        "and never repeat these instructions in the caption. "
                        "Adapt the format to the image_type. "
                        "For a chart, give the chart type, title, axes and units on the first line, "
                        "then a markdown table of the data points (prefix estimated values with ~), "
                        "then 1 or 2 sentences on the key trend, extremes or comparison. "
                        "For a table, give a markdown table with all cells, then 1 sentence on what it contains. "
                        "For a flowchart, name the process on the first line, then list the steps in order using the exact box texts, "
                        "writing decisions as 'If <condition>: go to step N, else step M'. "
                        "For a diagram, say what it represents on the first line, then write one bullet per relation as 'A -> B: <label>', "
                        "or an indented list for hierarchies; if it is too dense to transcribe, give its title, main components and purpose in 2 or 3 sentences. "
                        "For an infographic, give the title, then one bullet per key message with its figure. "
                        "For a screenshot, name the application and screen, then the main visible fields, menus, buttons and values, "
                        "then the action highlighted or implied by an arrow, a frame or a cursor. "
                        "For a photo, describe the subject, setting, notable details and visible text in 1 or 2 sentences. "
                        "For a technical_drawing, name the object represented, then one bullet per labeled part or dimension with units. "
                        "For a map, give the area covered, then the key places, labels and legend items. "
                        "For an equation, write the formula in LaTeX between $$, then 1 sentence on what it expresses if this is stated. "
                        "For a text_block, transcribe the text verbatim. "
                        "For a signature, leave the caption empty. "
                        "For a stamp, write 'Stamp of <organization>' if legible, plus the date if visible. "
                        "For a logo, write 'Logo of <organization>', or 'Logo' if unreadable. "
                        "For a qr_code, write 'QR code' or 'Barcode', followed by the URL or text printed next to it if visible. "
                        "For an icon, write 'Icon: <meaning>'. "
                        "For a decorative image, write at most 1 short sentence. "
                        "Otherwise, describe the content and purpose in 1 to 3 sentences."
                    ),
                },
            },
        },
    },
}


class MistralOCR(DocumentOCREngine):
    """OCR engine using Mistral's OCR API (https://docs.mistral.ai/).
    Runs on the whole document and returns markdown blocks,
    with images optionally replaced by their caption.
    Requires a Mistral API key.
    """

    API_URL = "https://api.mistral.ai/v1/ocr"
    # Image types rendered as a mere reference, without caption
    _CAPTIONLESS_IMAGE_TYPES = frozenset({"signature"})
    # HTTP status codes worth retrying
    _RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "mistral-ocr-4-1",
        image_captioning: bool = True,
        store_images: bool = False,
        skip_image_types: Iterable[str] = ("decorative", "icon"),
        max_request_mb: float = 40.0,
        timeout: float = 300.0,
        max_retries: int = 3,
    ) -> None:
        """Initializes the Mistral OCR engine.

        Args:
            api_key (str | None, optional): the Mistral API key.
                If None, read from the "MISTRAL_API_KEY" environment variable.
            model (str, optional): the OCR model to use. Must support block extraction
                (OCR 4 or newer). Defaults to "mistral-ocr-4-1".
            image_captioning (bool, optional): if True, images are categorized and captioned
                by the model, and the caption is added to the markdown. Increases the cost of the OCR.
                Defaults to True.
            store_images (bool, optional): if True, the images are returned as base64 data URIs
                in MarkdownDoc.images. Defaults to False.
            skip_image_types (Iterable[str], optional): the image types to remove from the markdown.
                Only used if image_captioning is True. Defaults to ("decorative", "icon").
            max_request_mb (float, optional): the maximum size of the document sent in a single request.
                Bigger documents are split by pages over several requests. Defaults to 40.0.
            timeout (float, optional): the timeout of a request, in seconds. Defaults to 300.0.
            max_retries (int, optional): the number of retries on network errors,
                rate limits and server errors. Defaults to 3.
        """
        unknown_types = set(skip_image_types) - set(IMAGE_TYPES)
        if unknown_types:
            raise ValueError(
                f"Unknown image types in skip_image_types: {sorted(unknown_types)}. Must be among {IMAGE_TYPES}."
            )
        self._api_key = api_key
        self._model = model
        self.image_captioning = image_captioning
        self.store_images = store_images
        self.skip_image_types = frozenset(skip_image_types)
        self.max_request_mb = max_request_mb
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        return "mistral"

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_key(self) -> str | None:
        return self._api_key or os.environ.get("MISTRAL_API_KEY")

    def __repr__(self) -> str:
        return (
            f"MistralOCR(model={self.model!r}, image_captioning={self.image_captioning}, "
            f"store_images={self.store_images})"
        )

    def validate(self) -> None:
        if not self.api_key:
            raise PdfParserException(
                'To use Mistral OCR, an API key must be provided: either MistralOCR(api_key="...") or the "MISTRAL_API_KEY" environment variable.'
            )

    def ocr_document(
        self, document: pymupdf.Document, page_start: int, page_end: int
    ) -> OCRDocument:
        self.validate()
        ocr_document = OCRDocument(
            engine=self.name, model=self.model, pages=list(range(page_start, page_end))
        )
        for batch_start, response in self._request_pages(
            document, page_start, page_end
        ):
            for page_response in response["pages"]:
                page_number = batch_start + page_response["index"]
                self._add_page(ocr_document, page_response, document[page_number])

        return ocr_document

    def _request_pages(
        self, document: pymupdf.Document, page_start: int, page_end: int
    ) -> list[tuple[int, dict[str, Any]]]:
        """Sends the pages to the API, splitting them over several requests
        if they are too heavy for a single one.

        Returns:
            list[tuple[int, dict[str, Any]]]: the responses, along with
                the number of the first page they hold.
        """
        sub_document = pymupdf.open()
        sub_document.insert_pdf(document, from_page=page_start, to_page=page_end - 1)  # type: ignore : missing typing in pymupdf
        pdf_bytes: bytes = sub_document.tobytes()  # type: ignore : missing typing in pymupdf
        sub_document.close()
        if (
            len(pdf_bytes) > self.max_request_mb * 1024 * 1024
            and page_end - page_start > 1
        ):
            middle = (page_start + page_end) // 2
            return self._request_pages(
                document, page_start, middle
            ) + self._request_pages(document, middle, page_end)

        return [(page_start, self._post(self._build_payload(pdf_bytes)))]

    def _build_payload(self, pdf_bytes: bytes) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": "data:application/pdf;base64,"
                + base64.b64encode(pdf_bytes).decode(),
            },
            "include_blocks": True,
            "include_image_base64": self.store_images,
        }
        if self.image_captioning:
            payload["bbox_annotation_format"] = IMAGE_ANNOTATION_FORMAT

        return payload

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sends the payload to the API, retrying on transient errors.

        Raises:
            PdfParserException: if the API returns an error.
        """
        request = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as e:
                if (
                    e.code not in self._RETRY_STATUS_CODES
                    or attempt == self.max_retries
                ):
                    raise PdfParserException(
                        f"Mistral OCR request failed with status {e.code}: {e.read().decode(errors='replace')}"
                    ) from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == self.max_retries:
                    raise PdfParserException(f"Mistral OCR request failed: {e}") from e
            time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def _add_page(
        self,
        ocr_document: OCRDocument,
        page_response: dict[str, Any],
        page: pymupdf.Page,
    ) -> None:
        """Converts the blocks of a page of the response to OCRBlocks
        and adds them, along with the images, to the OCRDocument."""
        page_number: int = page.number  # type: ignore : missing typing in pymupdf -> page.number : int
        dimensions = page_response["dimensions"]
        x_scale = page.rect.width / dimensions["width"]  # type: ignore : missing typing in pymupdf -> page.rect : Rect
        y_scale = page.rect.height / dimensions["height"]  # type: ignore : missing typing in pymupdf -> page.rect : Rect

        def to_rect(item: dict[str, Any]) -> pymupdf.Rect:
            return pymupdf.Rect(
                item["top_left_x"] * x_scale,
                item["top_left_y"] * y_scale,
                item["bottom_right_x"] * x_scale,
                item["bottom_right_y"] * y_scale,
            )

        images_by_id = {image["id"]: image for image in page_response["images"]}
        blocks: list[dict[str, Any]] = page_response.get("blocks") or [
            # Fallback for models that do not return blocks
            {
                "type": "text",
                "content": page_response["markdown"],
                "top_left_x": 0,
                "top_left_y": 0,
                "bottom_right_x": dimensions["width"],
                "bottom_right_y": dimensions["height"],
            }
        ]
        for block in blocks:
            match block["type"]:
                case "image" if block.get("image_id") in images_by_id:
                    image = self._make_image(
                        images_by_id[block["image_id"]],
                        page_number,
                        to_rect(block),
                        ocr_document,
                    )
                    if image.image_type in self.skip_image_types:
                        continue
                    ocr_document.images[image.id] = image
                    text = MistralOCR._image_to_markdown(image)
                case "signature":
                    signature_count = sum(
                        image_id.startswith("signature-")
                        for image_id in ocr_document.images
                    )
                    image = OCRImage(
                        id=f"signature-{signature_count}",
                        page=page_number,
                        bbox=to_rect(block),
                        image_type="signature",
                    )
                    ocr_document.images[image.id] = image
                    text = MistralOCR._image_to_markdown(image)
                case _:
                    image = None
                    text = block["content"].strip()
            if not text:
                continue
            ocr_document.blocks.append(
                OCRBlock(
                    type=block["type"],
                    text=text,
                    bbox=to_rect(block),
                    page=page_number,
                    order=len(ocr_document.blocks),
                    image_id=image.id if image else None,
                )
            )

    def _make_image(
        self,
        image_response: dict[str, Any],
        page_number: int,
        bbox: pymupdf.Rect,
        ocr_document: OCRDocument,
    ) -> OCRImage:
        """Builds the OCRImage of an image of the response."""
        image_id: str = image_response["id"]
        # ids may repeat when the document is split over several requests
        if image_id in ocr_document.images:
            image_id = f"page-{page_number}-{image_id}"
        image_type, caption = None, None
        if image_response.get("image_annotation"):
            try:
                annotation = json.loads(image_response["image_annotation"])
                image_type = annotation.get("image_type")
                caption = (annotation.get("caption") or "").strip() or None
            except json.JSONDecodeError:
                pass

        return OCRImage(
            id=image_id,
            page=page_number,
            bbox=bbox,
            image_type=image_type,
            caption=caption,
            base64=image_response.get("image_base64"),
        )

    @staticmethod
    def _image_to_markdown(image: OCRImage) -> str:
        """Renders an image as a markdown reference, followed by its caption as a quote."""
        markdown = f"![{image.image_type or 'image'}]({image.id})"
        if (
            image.caption
            and image.image_type not in MistralOCR._CAPTIONLESS_IMAGE_TYPES
        ):
            markdown += "\n" + "\n".join(
                f"> {line}".rstrip() for line in image.caption.splitlines()
            )

        return markdown
