from markdownify import markdownify

from .MarkdownChunkNorris import MarkdownChunkNorris


class HTMLChunkNorris(MarkdownChunkNorris):
    def __init__(self):
        super().__init__()

    def __call__(self, html_text: str, **kwargs) -> str:
        text = HTMLChunkNorris.apply_markdownify(html_text)

        return super().__call__(text, **kwargs)
    

    def apply_markdownify(html_text) -> str:
        """Applies markdownify to the html text

        Args:
            html_text (str): the text of the html file

        Returns:
            str: the markdownified string
        """
        md_text = markdownify(html_text, strip=["figure", "img"], bullets="-*+")

        return md_text
