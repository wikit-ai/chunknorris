# Getting started

So far, chunknorris contains implementation for chunking the following file types : **.md**, **.html** or **.pdf**. 

After you install ``chunknorris``, you can start getting your chunks either using python or the cli.

## Using Python

Here are code examples for chunking documents according to their file type:

=== ".md"

    ```py
    from chunknorris.parsers import MarkdownParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=MarkdownParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.md")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== ".html"

    ```py
    from chunknorris.parsers import HTMLParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=HTMLParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.html")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== ".pdf"

    ```py
    from chunknorris.parsers import PdfParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=PdfParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.pdf")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== "images"

    ```py
    from chunknorris.ml.ocr import MistralOCR
    from chunknorris.parsers import ImageParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=ImageParser(ocr_engine=MistralOCR()), # see the OCR page for the available engines
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.png") #  .jpg, .jpeg, .tiff, .bmp and .gif are also compatible.

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== ".docx"

    ```py
    from chunknorris.parsers import DocxParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=DocxParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.docx")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== ".csv"

    ```py
    from chunknorris.parsers import CSVParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=CSVParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.csv")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== ".xlsx"

    ```py
    from chunknorris.parsers import ExcelParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=ExcelParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.xslx") #  .xls, .odt or any excel-like file is compatible.

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

=== ".ipynb"

    ```py
    from chunknorris.parsers import JupyterNotebookParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import BasePipeline

    # Instanciate components
    pipeline = BasePipeline(
        parser=JupyterNotebookParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.ipynb")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.to_string())
    ```

Once you have your ``chunks``, you can easily print them of save them:

## Images

The images of markdown, HTML and .docx documents are kept in the markdown as ``![alt](id)`` references, and listed in ``md_doc.images`` and ``chunk.images``:

- images embedded as base64 (all the images of a .docx) get an id such as ``img-0.png``, and their data URI is stored in ``image.base64``.
- images pointing to a url get the url as id.
- the ``<figcaption>`` of an HTML image, or a blockquote right under a markdown image, is stored in ``image.caption``.

```py
from chunknorris.parsers import DocxParser

md_doc = DocxParser().parse_file("myfile.docx")
for image_id, image in md_doc.images.items():
    print(image_id, image.caption)

print(md_doc.to_string(include_images=True))  # embeds the base64 images in the markdown
```

Images of PDF and image files are found by OCR, see the [OCR](ocr.md) page.

## Using the CLI 

If you prefer, you may also run ``chunknorris`` in a terminal using:

```bash
chunknorris --filepath "path/to/myfile.pdf" # .pdf, .md or .html
```

In that case, the chunks will be saved in a JSON file, named ``<name_of_you_file>-chunks.json``.

You may also pass arguments to influence ``chunknorris``' behavior. Enter ``chunknorris -h`` in a terminal to see available options. Feel free to experiment 🧪 !