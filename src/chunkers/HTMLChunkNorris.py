from markdownify import markdownify

from .MarkdownChunkNorris import MarkdownChunkNorris

class HTMLChunkNorris(MarkdownChunkNorris):
    def __init__(self):
        super().__init__()


    def __call__(self, html_text: str, **kwargs) -> str:
        text = HTMLChunkNorris.apply_markdownify(html_text)
        titles = self.get_toc(text, **kwargs)
        chunks = self.get_chunks(titles, **kwargs)

        return chunks
    

    def apply_markdownify(html_text):
        """Applies markdownify to the html text

        Args:
            html_text (str): the text of the html file

        Returns:
            _type_: _description_
        """
        md_text = markdownify(
                html_text, strip=["figure", "img"], bullets="-*+"
            )
        
        return md_text