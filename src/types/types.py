from typing import TypedDict

Chunk = str

Chunks = list[Chunk]

class TocTree(TypedDict, total=False):
    id: int
    text: str
    level: int
    line_index: int
    content: str
    parents: TypedDict
    children: list[TypedDict]