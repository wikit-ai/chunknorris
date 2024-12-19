from typing import Literal, Optional

from nbformat import NotebookNode
from pydantic import BaseModel, ConfigDict


class JupyterNotebookCell(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    cell_type: Literal["markdown", "code", "raw"]
    metadata: NotebookNode
    source: str
    execution_count: Optional[int | None] = None
    outputs: Optional[list[NotebookNode]] = None
    attachments: Optional[NotebookNode] = None


class JupyterNotebookContent(BaseModel):
    """Utility schemas intended to be used for the parsing of notebooks.
    Ensures the notebook formatting in ok. Details about the format a the notebook
    can be found in nbformat's documentation : https://nbformat.readthedocs.io/en/latest/format_description.html#
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    metadata: NotebookNode
    nbformat: int
    nbformat_minor: int
    cells: list[JupyterNotebookCell]
