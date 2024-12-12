from chunknorris.chunkers.tools.tools import Chunk
from chunknorris.parsers.markdown.components import MarkdownLine

CHUNK_WITH_LINKS_IN = Chunk(
    headers=[MarkdownLine("# Header with [link](www.link.com)", line_idx=0)],
    content=[
        MarkdownLine(
            "This section has a [link](https://this-is-a-link.com/page)", line_idx=1
        ),
        MarkdownLine("\n", line_idx=2),
        MarkdownLine(
            "This section has an ![image](http://this/is/an/image.jpg 'Image title')",
            line_idx=3,
        ),
        MarkdownLine("\n", line_idx=4),
        MarkdownLine(
            "This is an [![image_link](this/is/an/image.jpg 'This is image title')](https://image_link.com)",
            line_idx=5,
        ),
    ],
    start_line=0,
)

CHUNK_WITH_LINKS_OUT = """# Header with link

This section has a link

This section has an image

This is an image_link"""
