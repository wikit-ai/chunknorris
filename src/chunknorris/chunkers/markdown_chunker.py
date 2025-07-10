from typing import Any, Literal

from ..core.components import Chunk, MarkdownDoc, MarkdownLine, TocTree
from ..decorators.decorators import timeit, validate_args
from .abstract_chunker import AbstractChunker


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
        hard_max_chunk_token_count: int | None = None,
        tokenizer: Any | None = None,
    ) -> None:
        """Initialize a Markdown chunker

        Args:
            max_headers_to_use (MaxHeadersToUse) : The maximum header level to consider (included).
                Headers with level lower than this wont be used to split chunks.
                For example, if 'h4' is set, then 'h5' and 'h6' headers won't be used.
                Must be a string of type 'hx' with x being the title level ranging from 1 to 6.
            max_chunk_word_count (int) : The maximum size a chunk can be (in words).
                It is a SOFT limit, meaning that chunks bigger that this will be chunked only if lower level headers if any are available."
            hard_max_chunk_word_count (int) : The true maximum size a chunk can be (in word).
                It is a HARD limit, meaning that chunks bigger by this limit will be split into subchunks.
            min_chunk_word_count (int) : The minimum size a chunk can be (in words).
                Chunks smaller than this will be discarded.
            hard_max_chunk_token_count (None | int) : The true maximum size a chunk can be (in tokens). If None, no token-based splitting will be done.
                It is a HARD limit, meaning that chunks bigger by this limit will be split into subchunks that are equivalent in terms of tokens count.
            tokenizer (Any | None) : The tokenizer to use. Can be any instance of a class that has 'encode' method such as tiktoken.
        """
        self.max_headers_to_use = max_headers_to_use
        self.max_chunk_word_count = max_chunk_word_count
        self.hard_max_chunk_word_count = hard_max_chunk_word_count
        self.min_chunk_word_count = min_chunk_word_count
        self.hard_max_chunk_token_count = hard_max_chunk_token_count
        self.tokenizer = tokenizer

    @timeit
    @validate_args
    def chunk(self, content: MarkdownDoc) -> list[Chunk]:
        """Chunks a parsed Markdown document.

        Args:
            content (MarkdownDoc): the markdown document to chunk.
                Might be the output of a chunknorris.Parser.

        Returns:
            list[Chunk]: the chunks.
        """
        toc_tree = self.get_toc_tree(content.content)
        chunks = self.get_chunks(toc_tree)

        return chunks

    def get_toc_tree(
        self,
        md_lines: list[MarkdownLine],
    ) -> TocTree:
        """Builds the table of content tree based on header.

        Args:
            md_lines (list[MarkdownLines]): the markdown lines.

        Returns:
            TocTree: the table of content.
        """
        max_header_level_to_use = int(self.max_headers_to_use[1])
        dummy_line = MarkdownLine("", line_idx=-1)
        tree = TocTree(title=dummy_line)
        current_node = tree
        id_cntr = 0
        for line in md_lines:
            if line.is_header and line.get_header_level() <= max_header_level_to_use:
                while (
                    current_node.parent is not None
                    and line.get_header_level() <= current_node.title.get_header_level()
                ):
                    current_node = current_node.parent
                current_node.add_child(
                    TocTree(
                        title=line,
                        id=id_cntr,
                    )
                )
                current_node = current_node.children[-1]
                id_cntr += 1
            else:
                current_node.content.append(line)

        return tree

    def get_chunks(self, toc_tree: TocTree) -> list[Chunk]:
        """Wrapper that build the chunk's texts, check
        that they fit in size, replace links formatting.

        Args:
            toc_tree (TocTree): the toc tree of the document.

        Returns:
            Chunks: the chunks text, formatted.
        """
        chunks = self.build_chunks(toc_tree)
        chunks = self.split_big_chunks_wordbased(chunks)
        chunks = self.split_big_chunks_tokenbased(chunks)
        chunks = self.remove_small_chunks(chunks)

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
            Chunks: list of chunk's texts.
        """
        if already_ok_chunks is None:
            already_ok_chunks = []

        current_chunk = MarkdownChunker._build_chunk(toc_tree_element)

        if current_chunk.word_count > self.max_chunk_word_count:
            if any(line.text.strip() for line in toc_tree_element.content):
                parent_headers = MarkdownChunker.get_parents_headers(toc_tree_element)
                current_chunk = Chunk(
                    headers=parent_headers + [toc_tree_element.title],
                    content=toc_tree_element.content,
                    start_line=toc_tree_element.title.line_idx,
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
        and recursively getting the content of children.

        Args:
            toc_tree_element (TocTree): the toc tree element.

        Returns:
            str: the chunk content. parent's headers + content.
        """
        parent_headers = MarkdownChunker.get_parents_headers(toc_tree_element)
        content = MarkdownChunker._build_chunk_content(toc_tree_element)

        return Chunk(
            headers=parent_headers,
            content=content,
            start_line=toc_tree_element.title.line_idx,
        )

    @staticmethod
    def _build_chunk_content(toc_tree_element: TocTree) -> list[MarkdownLine]:
        """Builds a chunk content (i.e without headers above)
        from a toc tree. It uses the toc tree's content, and recursively
        adds the header and content of its children.

        Args:
            toc_tree_element (TocTree): the toc tree (or element of toc tree).

        Returns:
            list[MarkdownLine]: the list of lines that belong to the chunk content (without the headers of parents).
        """
        content = [toc_tree_element.title] + toc_tree_element.content
        for child in toc_tree_element.children:
            content.extend(MarkdownChunker._build_chunk_content(child))

        return content

    @staticmethod
    def get_parents_headers(toc_tree_element: TocTree) -> list[MarkdownLine]:
        """Gets a list of the titles that are parent
        of the provided toc tree element. The list
        is ordered in descending order in terms of header level.

        Args:
            toc_tree_element (TocTree): the toc tree element.

        Returns:
            list[MarkdownLine]: the list of line that represent the parent's headers.
        """
        headers: list[MarkdownLine] = []
        while toc_tree_element.parent:
            toc_tree_element = toc_tree_element.parent
            headers.append(toc_tree_element.title)
        # remove empty string header, such as root header
        headers = [h for h in headers if h.text]

        return list(reversed(headers))

    def remove_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Removes chunks that have less words than the specified limit.

        Args:
            chunks (Chunks): the list of chunks.

        Returns:
            Chunks: the chunks with more words than the specified threshold.
        """
        return [c for c in chunks if c.word_count >= self.min_chunk_word_count]

    def split_big_chunks_wordbased(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """Splits the chunks that are too big.
        You may consider passing the kwarg "hard_max_chunk_word_count"
        to specify the limit size of the chunk (in words).

        Args:
            chunks (Chunks): The chunks obtained from the get_chunks() method.

        Returns:
            Chunks: the chunks, with big chunks splitted into smaller chunks.
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
        chunk titles at the beginning of each chunk.

        Args:
            chunk (Chunk): the chunk to split.
        """
        split_count = (chunk.word_count // self.hard_max_chunk_word_count) + 1
        split_word_size = chunk.word_count // split_count

        chunks: list[Chunk] = []
        line_buffer: list[MarkdownLine] = []
        headers_buffer = [None] * 7
        prev_buffer = headers_buffer.copy()
        for line in chunk.content:
            line_buffer.append(line)
            if line.is_header:
                header_level = line.get_header_level()
                headers_buffer[header_level:] = [None] * len(
                    headers_buffer[header_level:]
                )
                headers_buffer[header_level] = line
                continue
            # Do not split the chunk at this line to preserve tables, bullet points list and code blocks.
            elif line.is_bullet_point or line.isin_code_block or line.isin_table:
                continue
            current_word_count = len("\n".join(lb.text for lb in line_buffer).split())
            if current_word_count > split_word_size:
                chunks.append(
                    MarkdownChunker._create_new_chunk_from_lines(
                        chunk.headers + list(filter(None, prev_buffer)), line_buffer
                    )
                )
                line_buffer = []
                prev_buffer = headers_buffer
        if line_buffer:
            chunks.append(
                MarkdownChunker._create_new_chunk_from_lines(chunk.headers, line_buffer)
            )

        return chunks

    def split_big_chunks_tokenbased(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """Splits the chunks that are too big considering the provided tokenizer.

        Args:
            chunks (list[Chunk]): the chunks to split.

        Raises:
            ValueError: if the tokenizer is not provided.
            ValueError: if the tokenizer does not have 'encode' method.

        Returns:
            list[Chunk]: the chunks, with big chunks splitting into smaller chunks.
        """
        if self.hard_max_chunk_token_count is None:
            return chunks
        if self.tokenizer is None:
            raise ValueError(
                "Tokenizer is required when hard_max_chunk_token_count is set"
            )
        if not hasattr(self.tokenizer, "encode"):
            raise ValueError(
                "Tokenizer must have 'encode' methods that takes a string a intput and return a list of tokens."
            )

        splitted_chunks: list[Chunk] = []
        for chunk in chunks:
            splitted_chunks.extend(
                self._split_with_tokenizer(
                    chunk, self.tokenizer, self.hard_max_chunk_token_count
                )
            )
        return splitted_chunks

    @staticmethod
    def _split_with_tokenizer(
        chunk: Chunk, tokenizer: Any, hard_max_chunk_token_count: int
    ) -> list[Chunk]:
        """Split a chunk using the provided tokenizer and the hard_max_chunk_token_count."""
        chunk_tokens_count = len(tokenizer.encode(chunk.get_text()))
        if chunk_tokens_count < hard_max_chunk_token_count:
            return [chunk]
        else:
            n_splits = chunk_tokens_count // hard_max_chunk_token_count + 1
            tokens_per_split = chunk_tokens_count // n_splits
            line_buffer: list[MarkdownLine] = []
            initial_token_count = len(
                tokenizer.encode("\n\n".join([header.text for header in chunk.headers]))
            )
            current_token_count = initial_token_count
            new_chunks: list[Chunk] = []
            for line in chunk.content:
                line_token_count = len(tokenizer.encode(line.text + "\n"))
                current_token_count += line_token_count
                if current_token_count > tokens_per_split and line_buffer:
                    new_chunks.append(
                        MarkdownChunker._create_new_chunk_from_lines(
                            chunk.headers, line_buffer
                        )
                    )
                    line_buffer = []
                    current_token_count = initial_token_count + line_token_count
                line_buffer.append(line)
            if line_buffer:
                new_chunks.append(
                    MarkdownChunker._create_new_chunk_from_lines(
                        chunk.headers, line_buffer
                    )
                )

            return new_chunks

    @staticmethod
    def _create_new_chunk_from_lines(
        headers: list[MarkdownLine], lines: list[MarkdownLine]
    ) -> Chunk:
        """Utility function to create a chunk
        from a buffer of markdownLines.

        Args:
            headers (list[MarkdownLine]): the headers of the original chunk.
            lines (list[MarkdownLine]): The lines to put in the chunk.

        Returns:
            Chunk: the new chunk.
        """
        return Chunk(headers=headers, content=lines, start_line=lines[0].line_idx)
