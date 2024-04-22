import copy
import json
import re
import unicodedata
import tiktoken

from ..exceptions.exceptions import *
from ..types.types import *


class MarkdownChunkNorris:
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def __call__(self, md_text: str, **kwargs) -> Chunks:
        """Gets chunks from markdown string

        Args:
            md_text (str): the markdown string

        Returns:
            Chunks: the list of chunk's texts
        """
        toc_tree = self.get_toc_tree(md_text, **kwargs)
        chunks = self.get_chunks(toc_tree, **kwargs)

        return chunks

    @staticmethod
    def _check_string_argument_is_valid(
        argname: str, argvalue: str
    ):
        """Checks that an argument has a valid value

        Args:
            argname (str): the name of the argument
            argvalue (str): the value of the argument
        """
        allowed_values_dict =  {
            "header_style": ["setext", "atx"],
            "max_title_level_to_use": ["h1", "h2", "h3", "h4", "h5"],
            "link_placement": ["remove", "end_of_chunk", "in_sentence", "leave_as_markdown"],
            "chunk_tokens_exceeded_handling": ["raise_error", "split"],
        }
        allowed_values = allowed_values_dict[argname]
        assert argvalue in allowed_values, ValueError(
            f"Argument '{argname}' should be one of {allowed_values}. Got '{argvalue}'"
        )


    def _get_header_regex_patterns(self, header_style: str = "setext") -> dict:
        """Get the header regex patterns depending on the header_style

        Args:
            header_style (str, optional): the markdown header style. Must be 'atx' or 'setext'.
                Defaults to "setext".

        Returns:
            (dict) : a mapping between header name and regex patterns
        """
        self._check_string_argument_is_valid("header_style", header_style)
        patterns = {
            "h1": re.compile(r"(.+?)\n={3,}", re.MULTILINE),
            "h2": re.compile(r"(.+?)\n-{3,}", re.MULTILINE),
            "h3": re.compile(r"^(?:- )?(#{3} .+)", re.MULTILINE),
            "h4": re.compile(r"^(?:- )?(#{4} .+)", re.MULTILINE),
            "h5": re.compile(r"^(?:- )?(#{5} .+)", re.MULTILINE),
        }
        if header_style == "atx":
            patterns["h1"] = re.compile(r"^(?:- )?(#{1} .+)", re.MULTILINE)
            patterns["h2"] = re.compile(r"^(?:- )?(#{2} .+)", re.MULTILINE)

        return patterns

    
    def _convert_setext_to_atx(self, markdown_string:str) -> str:
        """Converts headers from setext style to markdown style

        Args:
            markdown_string (str): the markdown string

        Return:
            str: the string with formatted headers
        """
        regex_patterns = self._get_header_regex_patterns("setext")
        for match in re.finditer(regex_patterns["h1"], markdown_string):
            markdown_string = markdown_string.replace(match[0], f"# {match[1]}")
        for match in re.finditer(regex_patterns["h2"], markdown_string):
            markdown_string = markdown_string.replace(match[0], f"## {match[1]}")

        return markdown_string

    
    def get_toc_tree(
        self,
        markdown_string:str,
        max_title_level_to_use: str = "h4",
        header_style="setext",
        **kwargs) -> TocTree:
        """Builds the table of content tree based on header

        Args:
            markdown_string (str): the string, as markdown
            max_title_level_to_use (str, optional): the maximum title level to use. Headers with lower
                level than this won't be considered as headers. Defaults to "h4".
            header_style (str, optional): the type of header format. Defaults to "setext".

        Returns:
            TocTree: the table of content
        """
        MarkdownChunkNorris._check_string_argument_is_valid("header_style", header_style)
        MarkdownChunkNorris._check_string_argument_is_valid("max_title_level_to_use", max_title_level_to_use)
        if header_style == "setext":
            markdown_string = self._convert_setext_to_atx(markdown_string)
        title_types_to_consider = [
            f"h{i}" for i in range(1, int(max_title_level_to_use[1]) + 1)
        ]
        regex_patterns = self._get_header_regex_patterns("atx")
        lines = markdown_string.split('\n')
        tree = {"title": "", "children": [], "content": "", "id": -1, "line_index": -1, "level": -1, "parent": {}}
        current_level = -1
        current_node = tree
        id_cntr = 0
        for line_idx, line in enumerate(lines):
            for level, title_type in enumerate(title_types_to_consider):
                match = re.match(regex_patterns[title_type], line)
                if match:
                    title = match.group(1)
                    while level <= current_level:
                        current_node = current_node['parent']
                        current_level = current_node["level"]
                    new_node = {"title": title, "children": [], "content": "", "id": id_cntr, "line_index": line_idx, "level": level, "parent": current_node}
                    current_node["children"].append(new_node)
                    current_node = new_node
                    current_level = level
                    id_cntr += 1
                    break
            if not match:
                current_node["content"] += line + "\n"

        MarkdownChunkNorris._cleanup_tree_texts(tree)

        return tree
    

    @staticmethod
    def save_toc_tree(toc_tree:TocTree, output_path:str="toc_tree.json"):
        """Save the toc tree as json

        Args:
            toc_tree (TocTree): the toc tree to save
            output_path (str, optional): the output path. Defaults to "toc_tree.json".
        """
        dumpable_dict = copy.deepcopy(toc_tree)
        MarkdownChunkNorris._remove_circular_refs(dumpable_dict)
        with open(output_path, "w") as f:
            json.dump(dumpable_dict, f)


    @staticmethod
    def _remove_circular_refs(toc_tree_element:TocTree):
        """Recursively removes the circular ref in dict
        (used to save as json).

        Args:
            toc_tree_element (TocTree): the element of toc tree
        """
        if "parent" in toc_tree_element:
            del toc_tree_element["parent"]
        if "children" in toc_tree_element:
            for child in toc_tree_element["children"]:
                MarkdownChunkNorris._remove_circular_refs(child)

    
    @staticmethod
    def _cleanup_tree_texts(tree:TocTree):
        """Cleans up the texts at each 'content' key of the toc tree
        Uses recursion to go through each child
        Args:
            tree (TocTree): the toc tree
        """
        text = tree["content"]
        text = unicodedata.normalize("NFKC", text)
        # remove special characters
        special_chars = ["**", r"\*"]
        for char in special_chars:
            text = text.replace(char, "")
        # remove white spaces and newlines
        text = re.sub(r"\n\s*\n", "\n", text)
        text = text.rstrip().lstrip()
        tree["content"] = text
        if tree["children"]:
            for child in tree["children"]:
                tree = MarkdownChunkNorris._cleanup_tree_texts(child)


    @staticmethod
    def get_title_by_id(toc_tree:TocTree, id:int) -> TocTree:
        """Gets a toc tree using its id

        Args:
            toc_tree (TocTree): the toc tree
            id (int): the id of the title we are looking for. Defaults to int.

        Returns:
            TocTree: the element of title we were looking for
        """
        if toc_tree.get("id") == id:
            return toc_tree
        for child in toc_tree.get("children", []):
            target = MarkdownChunkNorris.get_title_by_id(child, id)
            if target:
                return target
            

    def get_chunks(self, toc_tree:TocTree, **kwargs) -> Chunks:
        """Wrapper that build the chunk's texts, check
        that they fit in size, replace links formatting.

        Args:
            toc_tree (TocTree): the toc tree of the documnet

        Returns:
            Chunks: the chunks text, formatted
        """
        chunks = MarkdownChunkNorris.get_chunks_texts(toc_tree, **kwargs)
        chunks = [MarkdownChunkNorris.change_links_format(c, **kwargs) for c in chunks]
        chunks = MarkdownChunkNorris.remove_small_chunks(chunks, **kwargs)
        chunks = self.remove_small_chunks(chunks, **kwargs)

        return chunks
            
    @staticmethod
    def get_chunks_texts(toc_tree_element:TocTree, already_ok_chunks:Chunks|None=None, **kwargs) -> Chunks:
        """Uses the toc tree to build the chunks. Uses recursion.
        Method :
        - build the chunk (= titles from sections above + section content + content of subsections)
        - if the chunk is too big:
            - save the section as title + content (if section has content)
            - subdivide section recursively using subsections
        - else save it as is

        Args:
            toc_tree_element (TocTree): _description_
            already_ok_chunks (Chunks, optional): the chunks already built.
                Used for recursion. Defaults to None.

        Returns:
            Chunks: list of chunk's texts
        """
        if not already_ok_chunks:
            already_ok_chunks = []

        current_chunk = MarkdownChunkNorris.build_chunk_text(toc_tree_element)

        if MarkdownChunkNorris._chunk_is_too_big(current_chunk, **kwargs):
            if toc_tree_element["content"]:
                parents = MarkdownChunkNorris.get_parents_headers(toc_tree_element)
                current_chunk = "\n".join(parents + [toc_tree_element["title"], toc_tree_element["content"]])
                already_ok_chunks.append(current_chunk)
            for child in toc_tree_element["children"]:
                already_ok_chunks = MarkdownChunkNorris.get_chunks_texts(child, already_ok_chunks, **kwargs)
        else:
            already_ok_chunks.append(current_chunk)
        
        return already_ok_chunks


    @staticmethod
    def build_chunk_text(toc_tree_element:TocTree) -> Chunk:
        """Builds a chunk by apposing the text of headers
        and recursively getting the content of children

        Args:
            toc_tree_element (TocTree): the toc tree element

        Returns:
            str: the chunk content. parent's headers + content
        """
        parents = MarkdownChunkNorris.get_parents_headers(toc_tree_element)
        content = MarkdownChunkNorris._build_chunk_content(toc_tree_element)

        return "\n".join(parents) + "\n" + content


    @staticmethod
    def _build_chunk_content(toc_tree_element:TocTree) -> str:
        """Builds a chunk content (i.e without headers above) 
        from a toc tree. It uses the toc tree's content, and recursively
        adds the header and content of its children

        Args:
            toc_tree_element (TocTree): the toc tree (or elment of toc tree)

        Returns:
            str: the text of the chunk (without the headers of parents)
        """
        text = toc_tree_element.get("title") + "\n" + toc_tree_element.get("content")
        if toc_tree_element.get("children"):
            for child in toc_tree_element.get("children"):
                text += "\n" + MarkdownChunkNorris._build_chunk_content(child)

        return text


    @staticmethod
    def get_parents_headers(toc_tree_element:TocTree) -> list[str]:
        """Gets a list of the titles that are parent
        of the provided toc tree element. The list
        is ordered in descending order in terms of header level.

        Args:
            toc_tree_element (TocTree): the toc tree element

        Returns:
            list[str]: the list of header's text
        """
        headers = []
        while toc_tree_element.get("parent"):
            toc_tree_element = toc_tree_element.get("parent")
            headers.append(toc_tree_element.get("title"))
        # remove empty string header, such as root header
        headers = [h for h in headers if h]

        return list(reversed(headers))


    @staticmethod
    def _chunk_is_too_big(chunk: str, max_chunk_word_length: int=200, **kwargs) -> bool:
        """Returns True if the chunk is bigger than the value
        specified as max_chunk_length in terms of word count

        Args:
            chunk (str): a chunk of text
            max_chunk_length (int): the max size of the chunk in words. Default to 200.

        Returns:
            bool: True if the chunk is too big, else false
        """
        return len(chunk.split()) > max_chunk_word_length


    @staticmethod
    def _header_has_children(toc_tree_element:TocTree) -> bool:
        """Mostly used for code comprehension.
        Returns True if the title has children.

        Args:
            toc_tree_element (TocTree): the header to check for children

        Returns:
            bool: True if the header has children
        """
        return bool(toc_tree_element.get("children"))

    @staticmethod
    def change_links_format(
        text, link_placement: str = "in_sentence", **kwargs
    ) -> str:
        """Removes the markdown format of the links in the text.
        The links are treated as specified by 'link_position':
        - remove : links are removed
        - in_sentence : the link is placed in the sentence, between parenthesis
        - end_of_chunk : all links are added at the end of the text
        - leave_as_markdown: leave links as markdown format

        Args:
            text (str): the text to find the links in
            link_placement (str, optional): How the links should be handled. Defaults to end_of_chunk.

        Returns:
            str: the formated text
        """
        MarkdownChunkNorris._check_string_argument_is_valid("link_placement", link_placement)
        if link_placement == "leave_as_markdown":
            return text

        patterns = {
            "image_as_link": r"\[!\[(.*?)\]\(.*?\)\]\((.*?)\)",
            "image": r"!\[(.*?)\]\((https?:[^\s'()]+).*?\)",
            "link": r"\[(.+?)\]\((https?:.+?)\)"
        }
        for pattern in patterns.values():
            matches = re.finditer(pattern, text)
            replacements = [(m[0], m[1], m[2]) for m in matches]
            if replacements is not None:
                text = MarkdownChunkNorris._handle_link_replacements(
                    text, replacements, link_placement=link_placement
                )

        return text

    @staticmethod
    def _handle_link_replacements(
        text: str,
        replacements: list[tuple[str, str, str]],
        link_placement: str = "in_sentence",
    ) -> str:
        """Handles the replacement of links in the text
        according to specified format

        Args:
            text (str): the text to replace the links ind
            replacements (list[tuple[str, str, str]]): the replacements. Is is a list of
                [(entire regex match, link's text, link's url)]
            link_placement (str, optional): _description_. Defaults to "in_sentence".

        Returns:
            str: the text with links modified
        """
        for i, m in enumerate(replacements):
            match link_placement:
                case "remove":
                    text = text.replace(m[0], m[1])
                case "end_of_chunk":
                    if i == 0:
                        text += "\nPour plus d'informations:\n"
                    text = text.replace(m[0], m[1])
                    text += f"- {m[1]}: {m[2]}"
                case "in_sentence":
                    text = text.replace(
                        m[0], f"{m[1]} (lien : {m[2]})"
                    )

        return text
    
    @staticmethod
    def remove_small_chunks(chunks: Chunks, min_chunk_word_count:int=15, **kwargs) -> Chunks:
        """Removes chunks that have less words than the specified limit

        Args:
            chunks (Chunks): _description_
            min_chunk_tokens (int, optional): the minimum size a chunk is allowed to be,
                in words. Chunks with less words than this are dicarded. Defaults to 15.
        Returns:
            Chunks: the chunks with more words than the specified threshold
        """
        return [c for c in chunks if len(c.split()) >= min_chunk_word_count]


    def split_big_chunks(
        self,
        chunks: Chunks,
        max_chunk_tokens: int = 8191,
        chunk_tokens_exceeded_handling: str = "raise_error",
        **kwargs,
    ) -> Chunks:
        """Checks that the chunks do not exceed the token limit, considered as a hard limit
        If chunk_tokens_exceeded_handling is:
        - "raise_error" -> it will raise an error in case a chunk to big is found
        for it to be investigated.
        - "split" -> Chunks exceeding the max size will be split to fit max_chunk_tokens

        Args:
            chunks (Chunks): The chunks obtained from the get_chunks() method
            max_chunk_tokens (int, optional): the maximum size a chunk is allowed to be,
                in tokens. Defaults to 8191.
            chunk_tokens_exceeded_handling (str, optional): whether or not error sould be raised if a big
                chunk is encountered, or split. Defaults to raise_error.
        """
        MarkdownChunkNorris._check_string_argument_is_valid("chunk_tokens_exceeded_handling", chunk_tokens_exceeded_handling)
        splitted_chunks = []
        for chunk in chunks:
            if self.get_token_count(chunk) < max_chunk_tokens:
                splitted_chunks.append(chunk)
            else:
                match chunk_tokens_exceeded_handling:
                    case "raise_error":
                        raise ChunkSizeExceeded(
                            (
                                f"Found chunk bigger than the specified token limit {max_chunk_tokens}:",
                                "You can disable this error and allow dummy splitting of this chunk by passing 'raise_error=False'",
                                f"The chunk : {chunk}",
                            )
                        )
                    case "split":
                        splitted_chunk = self._dummy_split_big_chunk(chunk, max_chunk_tokens)
                        splitted_chunks.extend(splitted_chunk)

        return splitted_chunks
    

    def get_token_count(self, text:Chunk) -> int:
        """Get the token count of a chunk

        Args:
            text (Chunk): the text to get the token count from

        Returns:
            int: the token count
        """
        return len(self.tokenizer.encode(text))


    def _dummy_split_big_chunk(
        self,
        chunk: Chunk,
        max_chunk_tokens: int = 8191,
    ) -> Chunks:
        """Splits the chunk so that the subchunks fit un max_chunk_size

        Args:
            chunk (Chunk): _description_
            max_chunk_tokens (int, optional): maximum chunk size. Defaults to 8191.

        Returns:
            Chunks: the subdivided chunks
        """
        token_count = self.get_token_count(chunk)
        if token_count < max_chunk_tokens:
            return [chunk]

        split_count = (token_count // max_chunk_tokens) + 1
        split_token_size = token_count // split_count
        tokenized_text = self.tokenizer.encode(chunk)
        splitted_text = [
            self.tokenizer.decode(
                tokenized_text[i * split_token_size : (i + 1) * split_token_size]
            )
            for i in range(split_count)
        ]

        return splitted_text
