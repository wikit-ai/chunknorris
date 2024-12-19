# Reference for `MarkdownParser`

The ``MarkdownParser`` is used to process markdown-formatted string or files to a ``MarkdownDoc`` object that can be fed to a chunker. **It will ensure that the markdown formatting is as expected by the chunker** (ATX heading style, parsing of metadata, etc...).

::: chunknorris.parsers.markdown.markdown_parser.MarkdownParser
    handler: python
    options:
      show_source: false