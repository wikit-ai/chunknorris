from pydantic import BaseModel


class AbstractInOutType(BaseModel):
    """
    Abstract In/Out type
    """

    content: str


class MarkdownString(AbstractInOutType):
    """A parsed Markdown Formatted String.
    Feats :
    - ATX header formatting.
    - Remove base64 images
    """


class HTMLString(AbstractInOutType):
    """A HTML Formatted String"""
