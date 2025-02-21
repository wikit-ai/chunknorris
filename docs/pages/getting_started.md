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
        print(chunk.get_text())
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
        print(chunk.get_text())
    ```

=== ".pdf"

    ```py
    from chunknorris.parsers import PdfParser
    from chunknorris.chunkers import MarkdownChunker
    from chunknorris.pipelines import PdfPipeline

    # Instanciate components
    pipeline = PdfPipeline(
        parser=PdfParser(),
        chunker=MarkdownChunker()
        )

    # Get some chunks !
    chunks = pipeline.chunk_file(filepath="myfile.pdf")

    # Save chunks
    pipeline.save_chunks(chunks)

    # Print chunks:
    for chunk in chunks:
        print(chunk.get_text())
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
        print(chunk.get_text())
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
        print(chunk.get_text())
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
        print(chunk.get_text())
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
        print(chunk.get_text())
    ```

Once you have your ``chunks``, you can easily print them of save them:

## Using the CLI 

If you prefer, you may also run ``chunknorris`` in a terminal using:

```bash
chunknorris --filepath "path/to/myfile.pdf" # .pdf, .md or .html
```

In that case, the chunks will be saved in a JSON file, named ``<name_of_you_file>-chunks.json``.

You may also pass arguments to influence ``chunknorris``' behavior. Enter ``chunknorris -h`` in a terminal to see available options. Feel free to experiment 🧪 !