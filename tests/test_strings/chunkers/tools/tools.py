from chunknorris.chunkers.tools.tools import Chunk


MD_WITH_LINKS_IN = """This section has a [link](https://this-is-a-link.com/page)

This section has an ![image](http://this/is/an/image.jpg 'Image title')

This is an [![image_link](this/is/an/image.jpg 'This is image title')](https://image_link.com)"""

CHUNK_WITH_LINKS_IN = Chunk(
    headers=["# Header with [link](www.link.com)"],
    content=MD_WITH_LINKS_IN,
    start_line=0,
)

CHUNK_WITH_LINKS_OUT = """# Header with link

This section has a link

This section has an image

This is an image_link"""
