from typing import Any, Literal, Protocol, runtime_checkable

from ..core.components import Chunk, MarkdownDoc, MarkdownLine, TocTree
from ..decorators.decorators import timeit, validate_args
from .abstract_chunker import AbstractChunker


@runtime_checkable
class SupportsEncode(Protocol):
    def encode(self, text: str) -> list[Any]: ...


class MarkdownChunker(AbstractChunker):
    # Class-level annotations for IDE support — not enforced at runtime.
    max_headers_to_use: Literal["h1", "h2", "h3", "h4", "h5", "h6"]
    max_chunk_word_count: int
    hard_max_chunk_word_count: int
    min_chunk_word_count: int
    hard_max_chunk_token_count: int | None
    tokenizer: SupportsEncode | None

    def __init__(
        self,
        max_headers_to_use: Literal["h1", "h2", "h3", "h4", "h5", "h6"] = "h4",
        max_chunk_word_count: int = 200,
        hard_max_chunk_word_count: int = 400,
        min_chunk_word_count: int = 15,
        hard_max_chunk_token_count: int | None = None,
        tokenizer: SupportsEncode | None = None,
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
            tokenizer (SupportsEncode | None) : The tokenizer to use. Can be any instance of a class that has 'encode' method such as tiktoken.
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
        id_counter = 0
        for line in md_lines:
            if line.is_header and (line_level := line.get_header_level()) <= max_header_level_to_use:
                while (
                    current_node.parent is not None
                    and line_level <= current_node.title.get_header_level()
                ):
                    current_node = current_node.parent
                current_node.add_child(
                    TocTree(
                        title=line,
                        id=id_counter,
                    )
                )
                current_node = current_node.children[-1]
                id_counter += 1
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
        parent_headers: list[MarkdownLine] | None = None,
    ) -> list[Chunk]:
        """Uses the toc tree to build the chunks.
        Method:
        - if the section (title + content + all descendants) fits within max_chunk_word_count:
            - save it as a single chunk
        - otherwise:
            - save the section's own content as a chunk (if non-empty)
            - subdivide into children recursively

        Args:
            toc_tree_element (TocTree): the TocTree for which the chunk should be built.
            parent_headers (list[MarkdownLine] | None): ancestor header lines. Defaults to None (root call).

        Returns:
            list[Chunk]: list of chunks.
        """
        result: list[Chunk] = []
        self._build_chunks_recursive(toc_tree_element, parent_headers or [], result)
        return result

    def _build_chunks_recursive(
        self,
        toc_tree_element: TocTree,
        parent_headers: list[MarkdownLine],
        result: list[Chunk],
    ) -> None:
        if toc_tree_element.estimate_word_count() > self.max_chunk_word_count:
            # Headers to pass down to children: parent headers + this section's title
            child_headers = (
                parent_headers + [toc_tree_element.title]
                if toc_tree_element.title.text
                else parent_headers
            )
            if any(line.text.strip() for line in toc_tree_element.content):
                result.append(
                    Chunk(
                        headers=child_headers,
                        content=toc_tree_element.content,
                        start_line=toc_tree_element.title.line_idx,
                    )
                )
            for child in toc_tree_element.children:
                self._build_chunks_recursive(child, child_headers, result)
        else:
            result.append(toc_tree_element.to_chunk(parent_headers))

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
        split_chunks: list[Chunk] = []
        for chunk in chunks:
            if chunk.word_count < self.hard_max_chunk_word_count:
                split_chunks.append(chunk)
            else:
                splitted_chunk = self._split_with_newlines(chunk)
                split_chunks.extend(splitted_chunk)

        return split_chunks

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
        # Index 0 is unused; header levels are 1-based (1–6).
        # seen_headers: tracks the most recent header at each level as we scan content.
        # subchunk_start_headers: snapshot of seen_headers at the start of the current sub-chunk,
        #   prepended as context headers to the sub-chunk being built.
        seen_headers: list[MarkdownLine | None] = [None] * 7
        subchunk_start_headers = seen_headers.copy()
        current_word_count = 0
        for line in chunk.content:
            line_buffer.append(line)
            current_word_count += len(line.text.split())
            if line.is_header:
                header_level = line.get_header_level()
                # Clear all deeper levels — a new header invalidates its descendants.
                for i in range(header_level + 1, 7):
                    seen_headers[i] = None
                seen_headers[header_level] = line
                continue
            # Do not split at these lines to preserve tables, bullet point lists and code blocks.
            elif line.is_bullet_point or line.isin_code_block or line.isin_table:
                continue
            if current_word_count > split_word_size:
                chunks.append(
                    MarkdownChunker._create_new_chunk_from_lines(
                        chunk.headers + list(filter(None, subchunk_start_headers)), line_buffer
                    )
                )
                line_buffer = []
                subchunk_start_headers = seen_headers.copy()
                current_word_count = 0
        if line_buffer:
            chunks.append(
                MarkdownChunker._create_new_chunk_from_lines(
                    chunk.headers + list(filter(None, seen_headers)), line_buffer
                )
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
        if not isinstance(self.tokenizer, SupportsEncode):
            raise ValueError(
                "Tokenizer must have an 'encode' method that takes a string as input and returns a list of tokens."
            )

        split_chunks: list[Chunk] = []
        for chunk in chunks:
            split_chunks.extend(
                self._split_with_tokenizer(
                    chunk, self.tokenizer, self.hard_max_chunk_token_count
                )
            )
        return split_chunks

    @staticmethod
    def _split_with_tokenizer(
        chunk: Chunk, tokenizer: SupportsEncode, hard_max_chunk_token_count: int
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
                # if line is too big for a single chunk -> split line and make chunks
                if line_token_count > hard_max_chunk_token_count:
                    if line_buffer:
                        new_chunks.append(
                            MarkdownChunker._create_new_chunk_from_lines(
                                chunk.headers, line_buffer
                            )
                        )
                        line_buffer = []
                    # split line in multiple chunks
                    new_chunks.extend(
                        MarkdownChunker._split_line_into_chunks(
                            line,
                            line_token_count,
                            hard_max_chunk_token_count,
                            chunk.headers,
                        )
                    )
                    continue
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

    @staticmethod
    def _split_line_into_chunks(
        line: MarkdownLine,
        line_token_count: int,
        hard_max_chunk_token_count: int,
        chunk_headers: list[MarkdownLine],
    ) -> list[Chunk]:
        """Splits a line that is too big to fit in a chunk
        into multiple lines, each producing a chunk.

        NOTE: to avoid the need of tokenizer.decode()
        we split be character.

        Args:
            line (MarkdownLine): the line to split.
            line_token_count (int): the token count of the line.
            hard_max_chunk_token_count (int): the maximum number of token a chunk can be.
            chunk_headers (list[MarkdownLine]): the headers of the chunk.
        """
        n_splits = line_token_count // hard_max_chunk_token_count + 1
        n_chars = len(line.text)
        n_chars_per_split = n_chars // n_splits + 1
        line_splits = [
            MarkdownLine(
                text=line.text[n_chars_per_split * i : n_chars_per_split * (i + 1)],
                line_idx=line.line_idx,  # WARNING : This creates multiple lines with same idx.
                isin_code_block=line.isin_code_block,
                page=line.page,
            )
            for i in range(n_splits)
        ]

        return [
            MarkdownChunker._create_new_chunk_from_lines(chunk_headers, [line_split])
            for line_split in line_splits
        ]
