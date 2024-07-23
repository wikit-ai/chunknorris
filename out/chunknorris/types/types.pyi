Chunk = str
Chunks = list[Chunk]

class TocTree:
    id: int
    text: str
    level: int
    line_index: int
    content: str
    parents: dict
    children: list[dict]
