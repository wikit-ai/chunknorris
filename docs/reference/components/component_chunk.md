# Reference for `Chunk`

The ``Chunk`` is the entity returned by ``chunknorris``'s chunkers. It contains various elements related to the chunks : it's text content, headers, the pages it comes from (if from paginated documents) etc. 
You might essentially need to use ``Chunk.get_text()`` to get the cleaned chunk's content as text **preceded by its headers**. 

::: chunknorris.core.components.Chunk
    handler: python
    options:
      show_source: false