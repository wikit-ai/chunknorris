import re
from typing import Literal

from .abstract_chunker import AbstractChunker
from .tools.tools import Chunk, TocTree
from ..types.types import MarkdownString


class MarkdownChunker(AbstractChunker):
    max_headers_to_use: str
    max_chunk_word_count: int
    hard_max_chunk_word_count: int
    min_chunk_word_count: int

    def __init__(
        self,
        max_headers_to_use: Literal["h1", "h2", "h3", "h4", "h5", "h6"] = "h4",
        max_chunk_word_count: int = 200,
        hard_max_chunk_word_count: int = 400,
        min_chunk_word_count: int = 15,
    ) -> None:
        """Initialize a Markdown chunker

        Args:
            max_headers_to_use (MaxHeadersToUse) : The maximum header level to consider (included).
                Headers with level lower than this wont be used to split chunks.
                For example, if 'h4' is set, then 'h5' and 'h6' headers won't be used.
                Must be a string of type 'hx' with x being the title level ranging from 1 to 6.
            max_chunk_word_count (int) : The maximum size a chunk can be (in words).
                It is a SOFT limit, meaning that chunks bigger that this size will be chunked using lower level headers if any are available."
            hard_max_chunk_word_count (int) : The true maximum size a chunk can be (in word).
                It is a HARD limit, meaning that chunks bigger by this limit will be split into subchunks.
                ChunkNorris will try to equilibrate the size of resulting subchunks. It should be greater than max_chunk_word_count."
            min_chunk_word_count (int) : The minimum size a chunk can be (in words).
                Chunks lower than this will be discarded.
        """
        self.max_headers_to_use = max_headers_to_use
        self.max_chunk_word_count = max_chunk_word_count
        self.hard_max_chunk_word_count = hard_max_chunk_word_count
        self.min_chunk_word_count = min_chunk_word_count

    @property
    def _header_regex_patterns(self) -> dict[str, re.Pattern[str]]:
        """The header regex patterns for headers."""
        patterns = {
            "h1": re.compile(r"^(?:- )?(#{1} .+)", re.MULTILINE),
            "h2": re.compile(r"^(?:- )?(#{2} .+)", re.MULTILINE),
            "h3": re.compile(r"^(?:- )?(#{3} .+)", re.MULTILINE),
            "h4": re.compile(r"^(?:- )?(#{4} .+)", re.MULTILINE),
            "h5": re.compile(r"^(?:- )?(#{5} .+)", re.MULTILINE),
        }

        return patterns

    def chunk_string(self, string: MarkdownString) -> list[Chunk]:
        """Chunks a Markdown formatted string

        Returns:
            Chunks: the chunks
        """
        toc_tree = self.get_toc_tree(string.content)
        chunks = self.get_chunks(toc_tree)

        return chunks

    def get_toc_tree(
        self,
        md_string: str,
    ) -> TocTree:
        """Builds the table of content tree based on header

        Args:
            md_string (str): the markdown formatted string

        Returns:
            TocTree: the table of content
        """
        headers_patterns_to_use = [
            self._header_regex_patterns[f"h{i}"]
            for i in range(1, int(self.max_headers_to_use[1]) + 1)
        ]
        tree = TocTree()
        current_node = tree
        id_cntr = 0
        match = None
        within_code_block = False
        for line_idx, line in enumerate(md_string.split("\n")):
            if line.startswith("```") and not "```" in line[3:]:
                within_code_block = not within_code_block
            if not within_code_block:
                for level, pattern in enumerate(headers_patterns_to_use):
                    match = re.match(pattern, line)
                    if match and not within_code_block:
                        title = match.group(1)
                        while (
                            current_node.parent is not None
                            and level <= current_node.level
                        ):
                            current_node = current_node.parent
                        current_node.add_child(
                            TocTree(
                                title=title,
                                id=id_cntr,
                                line_index=line_idx,
                                level=level,
                            )
                        )
                        current_node = current_node.children[-1]
                        id_cntr += 1
                        break
            if within_code_block or not match:
                current_node.content += line + "\n"

        return tree

    def get_chunks(self, toc_tree: TocTree) -> list[Chunk]:
        """Wrapper that build the chunk's texts, check
        that they fit in size, replace links formatting.

        Args:
            toc_tree (TocTree): the toc tree of the document

        Returns:
            Chunks: the chunks text, formatted
        """
        chunks = self.build_chunks(toc_tree)
        chunks = self.remove_small_chunks(chunks)
        chunks = self.split_big_chunks(chunks)

        return chunks

    def build_chunks(
        self,
        toc_tree_element: TocTree,
        already_ok_chunks: list[Chunk] | None = None,
    ) -> list[Chunk]:
        """Uses the toc tree to build the chunks. Uses recursion.
        Method :
        - build the chunk (= titles from sections above + section content + content of subsections)
        - if the chunk is too big:
            - save the section as title + content (if section has content)
            - subdivide section recursively using subsections
        - else save it as is

        Args:
            toc_tree_element (TocTree): the TocTree for which the chunk should be build
            already_ok_chunks (Chunks, optional): the chunks already built.
                Used for recursion. Defaults to None.

        Returns:
            Chunks: list of chunk's texts
        """
        if not already_ok_chunks:
            already_ok_chunks = []

        current_chunk = MarkdownChunker._build_chunk(toc_tree_element)

        if current_chunk.word_count > self.max_chunk_word_count:
            if toc_tree_element.content.strip():
                parent_headers = MarkdownChunker.get_parents_headers(toc_tree_element)
                current_chunk = Chunk(
                    headers=parent_headers + [toc_tree_element.title],
                    content=toc_tree_element.content,
                    start_line=toc_tree_element.line_index,
                )
                already_ok_chunks.append(current_chunk)
            for child in toc_tree_element.children:
                already_ok_chunks = self.build_chunks(child, already_ok_chunks)
        else:
            already_ok_chunks.append(current_chunk)

        return already_ok_chunks

    @staticmethod
    def _build_chunk(toc_tree_element: TocTree) -> Chunk:
        """Builds a chunk by apposing the text of headers
        and recursively getting the content of children

        Args:
            toc_tree_element (TocTree): the toc tree element

        Returns:
            str: the chunk content. parent's headers + content
        """
        parent_headers = MarkdownChunker.get_parents_headers(toc_tree_element)
        content = MarkdownChunker._build_chunk_content(toc_tree_element)

        return Chunk(
            headers=parent_headers,
            content=content,
            start_line=toc_tree_element.line_index,
        )

    @staticmethod
    def _build_chunk_content(toc_tree_element: TocTree) -> str:
        """Builds a chunk content (i.e without headers above)
        from a toc tree. It uses the toc tree's content, and recursively
        adds the header and content of its children

        Args:
            toc_tree_element (TocTree): the toc tree (or element of toc tree)

        Returns:
            str: the text of the chunk (without the headers of parents)
        """
        text = toc_tree_element.title + "\n\n" + toc_tree_element.content
        for child in toc_tree_element.children:
            text += "\n\n" + MarkdownChunker._build_chunk_content(child)

        return text

    @staticmethod
    def get_parents_headers(toc_tree_element: TocTree) -> list[str]:
        """Gets a list of the titles that are parent
        of the provided toc tree element. The list
        is ordered in descending order in terms of header level.

        Args:
            toc_tree_element (TocTree): the toc tree element

        Returns:
            list[str]: the list of header's text
        """
        headers: list[str] = []
        while toc_tree_element.parent:
            toc_tree_element = toc_tree_element.parent
            headers.append(toc_tree_element.title)
        # remove empty string header, such as root header
        headers = [h for h in headers if h]

        return list(reversed(headers))

    def remove_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Removes chunks that have less words than the specified limit

        Args:
            chunks (Chunks): the list of chunks

        Returns:
            Chunks: the chunks with more words than the specified threshold
        """
        return [c for c in chunks if c.word_count >= self.min_chunk_word_count]

    def split_big_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """Splits the chunks that are too big.
        You may consider passing the kwarg "hard_max_chunk_word_count"
        to specify the limit size of the chunk (in words)

        Args:
            chunks (Chunks): The chunks obtained from the get_chunks() method

        Returns:
            Chunks: the chunks, with big chunks splitting into smaller chunks
        """
        splitted_chunks: list[Chunk] = []
        for chunk in chunks:
            if chunk.word_count < self.hard_max_chunk_word_count:
                splitted_chunks.append(chunk)
            else:
                splitted_chunk = self._split_with_newlines(chunk)
                splitted_chunks.extend(splitted_chunk)

        return splitted_chunks

    def _split_with_newlines(
        self,
        chunk: Chunk,
    ) -> list[Chunk]:
        """Split chunks based on newlines. Adds the
        chunk titles at the beginning of each chunk

        Args:
            chunk (Chunk): the chunk to split
        """
        split_count = (chunk.word_count // self.hard_max_chunk_word_count) + 1
        split_word_size = chunk.word_count // split_count

        chunks: list[Chunk] = []
        current_chunk_lines: list[str] = []
        headers_lines: list[str | None] = [None] * 6  # to store the headers
        headers_lines_buffer = headers_lines.copy()
        prev_start_line = chunk.start_line
        within_code_block = False
        for line_idx, line in enumerate(chunk.content.split("\n")):
            if line.startswith("```") and not "```" in line[3:]:
                within_code_block = not within_code_block
            if line.startswith("#") and not within_code_block:  # header
                header_lvl = len(line) - len(line.lstrip("#")) - 1
                headers_lines[header_lvl:] = [None] * (len(headers_lines) - header_lvl)
                headers_lines[header_lvl] = line
            current_chunk_lines.append(line)
            if len("\n".join(current_chunk_lines).split()) > split_word_size:
                headers = list(filter(None, headers_lines_buffer))
                new_chunk = Chunk(
                    headers=chunk.headers,
                    content="\n\n".join(headers)
                    + "\n\n"
                    + "\n".join(current_chunk_lines),
                    start_line=prev_start_line,
                )
                chunks.append(new_chunk)
                prev_start_line = chunk.start_line + line_idx
                current_chunk_lines = []
                headers_lines_buffer = headers_lines.copy()
        if current_chunk_lines:
            headers = list(filter(None, headers_lines))
            new_chunk = Chunk(
                headers=chunk.headers,
                content="\n\n".join(headers) + "\n\n" + "\n".join(current_chunk_lines),
                start_line=prev_start_line,
            )
            chunks.append(new_chunk)

        return chunks
