# OCR

Some PDF documents, such as scanned documents, hold no text but only images of text. To get their content, ``PdfParser`` relies on OCR.

When OCR runs is controlled by the ``use_ocr`` argument:

- ``"auto"`` (default): OCR is used only where no text is found.
- ``"always"``: OCR is always used.
- ``"never"``: OCR is never used. Documents without text raise a ``TextNotFoundException``.

How OCR runs is controlled by the ``ocr_engine`` argument. Here are code examples for each OCR engine:

=== "Tesseract (default)"

    Runs locally, page per page. In ``"auto"`` mode, only the pages without text go through OCR.

    Requires [Tesseract](https://pymupdf.readthedocs.io/en/latest/installation.html#enabling-integrated-ocr-support) to be installed, and the ``TESSDATA_PREFIX`` environment variable to point to the folder holding the ``<language>.traineddata`` files.

    ```py
    from chunknorris.ml.ocr import TesseractOCR
    from chunknorris.parsers import PdfParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=PdfParser(
            use_ocr="auto",
            ocr_engine=TesseractOCR(language="fra+eng"),
            ),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.pdf")
    ```

=== "Mistral OCR"

    Runs on [Mistral's OCR API](https://docs.mistral.ai/), on the whole document. In ``"auto"`` mode, the document goes through OCR only if no text is found in it.

    Requires a Mistral API key, either passed as ``MistralOCR(api_key="...")`` or set as the ``MISTRAL_API_KEY`` environment variable. No extra dependency is needed.

    ```py
    from chunknorris.ml.ocr import MistralOCR
    from chunknorris.parsers import PdfParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=PdfParser(
            use_ocr="auto",
            ocr_engine=MistralOCR(
                image_captioning=True,  # describe the images in the markdown
                store_images=False,  # keep the images as base64 in the parsed document
                ),
            ),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.pdf")

    # Images referenced in each chunk
    for chunk in chunks:
        for image_id, image in chunk.images.items():
            print(image_id, image.image_type, image.caption)
    ```

    With ``image_captioning=True``, each image is categorized (chart, screenshot, photo, signature...) and replaced in the markdown by a reference followed by its caption:

    ```md
    ![screenshot](img-0.jpeg)
    > Application: Gmail web interface
    > Buttons: Send (blue), Discard (red)
    ```

    Use ``skip_image_types`` to remove some categories of images from the markdown. Defaults to ``("decorative", "icon")``.

    !!! note
        Documents parsed with Mistral OCR bypass the regular parsing pipeline of ``PdfParser``. Methods relying on it, such as ``get_toc()`` or ``get_tables()``, are not available on them.

## Knowing whether OCR was used

After parsing, ``parser.parsed_using_ocr`` tells whether OCR was used. The parsed ``MarkdownDoc`` also holds the details in its metadata:

```py
parser = PdfParser(ocr_engine=MistralOCR())
md_doc = parser.parse_file("my_scanned_file.pdf")

print(parser.parsed_using_ocr)  # True
print(md_doc.metadata["ocr"])  # {'engine': 'mistral', 'model': 'mistral-ocr-4-1', 'pages': [0, 1, 2]}
```

## Using the CLI

The OCR engine can also be selected in the CLI:

```bash
chunknorris --filepath "path/to/myfile.pdf" --use_ocr auto --ocr_engine mistral
```
