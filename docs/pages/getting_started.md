# Getting started

So far, chunknorris contains implementation for chunking the following file types : **.md**, **.html** or **.pdf**. 

After you install ``chunknorris``, you can start getting your chunks either using python or the cli.

## Using Python

Here are code examples for chunking documents each file type using python:

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

## Using the CLI 

If you prefer, you may also run ``chunknorris`` in a terminal using:

```bash
chunknorris --filepath "path/to/myfile.pdf" # .pdf, .md or .html
```

In that case, the chunks will be saved in a JSON file, named ``<name_of_you_file>-chunks.json``.

You may also pass arguments to influence ``chunknorris``' behavior. Enter ``chunknorris -h`` in a terminal to see available options. Feel free to experiment 🧪 !