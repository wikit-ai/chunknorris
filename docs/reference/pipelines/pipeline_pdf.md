# Reference for `PdfPipeline`

Compared to the ``BasePipeline``, the ``PdfPipeline`` handles extra functionnality specific to .pdf document. For example, it will switch between chunking using headers or chunking by page depending on whether of not header have been found or if the .pdf is derived from Powerpoint.

::: chunknorris.pipelines.pdf_pipeline.PdfPipeline
    handler: python
    options:
      show_source: false