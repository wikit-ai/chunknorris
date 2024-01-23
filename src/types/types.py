from typing import List, TypedDict


class ShortTitle(TypedDict, total=True):
    id: int
    text: str
    level: int
    start_position: int
    end_position: int


class Title(TypedDict, total=False):
    id: int
    text: str
    level: int
    start_position: int
    end_position: int
    content: str
    parents: List[ShortTitle]
    children: List[ShortTitle]


Titles = List[Title]


class Chunk(TypedDict, total=True):
    id: str
    token_count: int
    word_count: int
    source_doc: str
    text: str


Chunks = List[Chunk]
