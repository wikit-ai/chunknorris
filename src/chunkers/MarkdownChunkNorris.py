import re
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
            str: _description_
        """
        titles = self.get_toc(md_text, **kwargs)
        chunks = self.get_chunks(titles, **kwargs)

        return chunks


    @staticmethod
    def _check_string_argument_is_valid(
        argname: str, argvalue: str, allowed_values: list[str]
    ):
        """Checks that an argument has a valid value

        Args:
            argname (str): the name of the argument
            argvalue (str): the value of the argument
            allowed_values (list[str]): list of allowed values
        """
        assert argvalue in allowed_values, ValueError(
            f"Argument '{argname}' should be one of {allowed_values}. Got '{argvalue}'"
        )


    def get_toc(self, text: str, **kwargs) -> Titles:
        """Get the Table Of Content i.e the list
        of titles and their relation with each other

        Args:
            text (str): the text to get the toc from

        Returns:
            Titles: list of dicts describing the titles. For more info, look at Title class
        """
        titles = self.get_titles(text, **kwargs)
        titles = MarkdownChunkNorris._get_text_before_titles(titles)
        for title in titles:
            title["children"] = MarkdownChunkNorris._get_titles_children(title, titles)
            title["parents"] = MarkdownChunkNorris._get_titles_parents(title, titles)
        titles = MarkdownChunkNorris._get_titles_content(titles, text)

        return titles


    def _get_header_regex_patterns(self, header_style:str="setext") -> dict:
        """Get the header regex patterns depending on the header_style

        Args:
            header_style (str, optional): the markdown header style. Must be 'atx' or 'setext'.
                Defaults to "setext".

        Returns:
            (dict) : a mapping between header name and regex patterns 
        """
        self._check_string_argument_is_valid("header_style", header_style, ["setext", "atx"])
        patterns = {
            "h1": re.compile(r"(.+?)\n={3,}", re.MULTILINE),
            "h2": re.compile(r"(.+?)\n-{3,}", re.MULTILINE),
            "h3": re.compile(r"^#{3} (.+)\n", re.MULTILINE),
            "h4": re.compile(r"^#{4} (.+)\n", re.MULTILINE),
            "h5": re.compile(r"^#{5} (.+)\n", re.MULTILINE),
        }
        if header_style == "atx":
            patterns["h1"] = re.compile(r"^#{1} (.+)\n", re.MULTILINE)
            patterns["h2"] = re.compile(r"^#{2} (.+)\n", re.MULTILINE)

        return patterns


    def get_titles(self, text: str, max_title_level_to_use: str = "h4", header_style = "setext", **kwargs) -> Titles:
        """Gets the titles (=headers h1, h2 ...) in the text
        using regex

        Args:
            text (str): the titles to look for titles in
            max_title_level_to_use (str, optional): the max level of headers to look for (included). Defaults to "h4".

        Returns:
            Titles: a list of dicts describing titles. For more info, look at Title class
        """
        MarkdownChunkNorris._check_string_argument_is_valid(
            "max_title_level", max_title_level_to_use, ["h1", "h2", "h3", "h4", "h5"]
        )

        # Get the titles types to consider (h1, h2, ...)
        title_types_to_consider = [
            f"h{i}" for i in range(1, int(max_title_level_to_use[1]) + 1)
        ]
        regex_patterns = self._get_header_regex_patterns(header_style)
        titles = []
        for title_level, title_type in enumerate(title_types_to_consider):
            regex_pattern = regex_patterns[title_type]
            for match in re.finditer(regex_pattern, text):
                title_text = match.group(1)
                start_position = match.start()
                end_position = match.end()
                titles.append(
                    {
                        "text": title_text,
                        "level": title_level,
                        "start_position": start_position,
                        "end_position": end_position,
                    }
                )

        # add id to each title
        titles = [{"id": i} | title for i, title in enumerate(titles)]

        return titles


    @staticmethod
    def _get_titles_content(titles: Titles, text: str) -> Titles:
        """Get the text content of each title, meaning
        the text that is between the title and the next title

        Args:
            titles (Titles): the titles found in the text
            text (str): the text from which titles were extracted

        Returns:
            Titles: the titles, with a "content" section added
        """
        # make sure titles are sorted by order of appearance
        titles = sorted(titles, key=lambda x: x["start_position"])
        for i, title in enumerate(titles):
            if i + 1 < len(titles):
                next_title = titles[i + 1]
                content = text[max(0, title["end_position"]) : next_title["start_position"]]
            else:  # its the last title
                content = text[max(0, title["end_position"]) :]
            title["content"] = content

        return titles

    @staticmethod
    def cleanup_text(text: str) -> str:
        """Cleans up a text using various operations

        Args:
            text (str): the text to cleanup

        Returns:
            str: the cleanedup text
        """
        # remove special characters
        special_chars = ["**", "\xa0", "\*"]
        for char in special_chars:
            text = text.replace(char, "")
        # remove white spaces and newlines
        text = re.sub(r'\n\s*\n', '\n', text)

        return text

    @staticmethod
    def _get_titles_children(title: Title, titles: Titles) -> list[ShortTitle]:
        """Gets the children of a title among titles,
        meaning the titles of its subsections.

        A child is:
         - after in terms of position (higher 'start_position')
         - lower in terms of level (higher 'level')

        Args:
            title (Title): The title for which we want the children
            titles (Titles): The titles found in the text

        Returns:
            Titles: A list of child titles
        """
        # in the children, put the titles without their "content", "children" or "parents" fields
        child_keys_to_keep = ["id", "text", "level", "start_position", "end_position"]
        title_of_next_section = MarkdownChunkNorris._get_title_of_next_section(title, titles)
        if title_of_next_section is None:
            return [
                {k: v for k, v in t.items() if k in child_keys_to_keep}
                for t in titles
                if t["start_position"] > title["end_position"]
            ]
        else:
            return [
                {k: v for k, v in t.items() if k in child_keys_to_keep}
                for t in titles
                if t["start_position"] > title["end_position"]
                and t["end_position"] < title_of_next_section["start_position"]
            ]

    @staticmethod
    def _get_titles_parents(title: Title, titles: Titles) -> list[ShortTitle]:
        """Gets the parents of the specified title.
        Parents are titles of the section that the specified title
        belongs to.

        Args:
            title (Title): The title we want the parents of
            titles (Titles): The titles found in the text

        Returns:
            list[ShortTitle]: A list of parents
        """
        # in the parents, put the titles without their "content", "children" or "parents" fields
        parent_keys_to_keep = ["id", "text", "level", "start_position", "end_position"]
        parents = []
        # find the title's parent, and consecutive parents of parents
        direct_parent = title
        while direct_parent:
            direct_parent = MarkdownChunkNorris._get_direct_parent_of_title(
                direct_parent, titles
            )
            if direct_parent is not None:
                direct_parent = {
                    k: v for k, v in direct_parent.items() if k in parent_keys_to_keep
                }
                parents.append(direct_parent)

        return parents

    @staticmethod
    def _get_direct_parent_of_title(title: Title, titles: Titles) -> Title:
        """Considering a title, gets the direct parent of a title,
        meaning the title of the section this title belongs to.

        The direct parent is:
        - Higher in terms of level (lower level index)
        - has its position in text before the title considered

        Example : considering an h2, its direct parent would be
        the h1 before it.

        WARNING: May return None if no parent title is found

        Args:
            title (Title): the title to consider
            titles (Titles): the titles found in the text

        Returns:
            Title: the direct parent of the provided Title
        """
        direct_parent = [
            t
            for t in titles
            if t["level"] < title["level"]
            and t["end_position"] < title["start_position"]
        ]
        if not direct_parent:
            return None

        return max(direct_parent, key=lambda x: x["start_position"])

    @staticmethod
    def _get_title_of_next_section(title: Title, titles: Titles) -> Title:
        """Considering a title, gets the title of the next section.
        The next section comes when we reach a title that as a
        equal or higher level than the provided title.

        Example: considering a h3, the next section's title would be when
        we encounter an other h3 or h2 or h1

        WARNING: May return None if no next section's title is found

        Args:
            title (Title): The title that we consider
            titles (Titles): list of titles of the document

        Returns:
            Title: The title of next section
        """
        same_level_titles = [
            t
            for t in titles
            if t["level"] <= title["level"]
            and t["start_position"] > title["end_position"]
        ]
        # if we have no next sections's title
        if not same_level_titles:
            return None

        return min(same_level_titles, key=lambda x: x["start_position"])

    @staticmethod
    def _get_title_of_next_subsection(title: Title, titles: Titles) -> Title:
        """Considering a title, gets the title of the next subsection.
        The next subsection comes when we reach a title that as a
        lower level than the provided title.

        Example: considering a h3, the next section's title would be when
        we encounter an other h4 or h5

        WARNING: May return None if no next section's title is found

        Args:
            title (Title): The title that we consider
            titles (Titles): list of titles of the document

        Returns:
            Title: The title of next section
        """
        same_level_titles = [
            t
            for t in titles
            if t["level"] > title["level"]
            and t["start_position"] > title["end_position"]
        ]
        # if we have no next sections's title
        if not same_level_titles:
            return None

        return min(same_level_titles, key=lambda x: x["start_position"])

    @staticmethod
    def _get_title_using_condition(
        titles: Titles, conditions: dict, raise_errors: bool = True
    ) -> Title:
        """Get the titles corresponding to the conditions.
        The conditions must be a dict. The method check that the keys-values pairs of conditions
        exist in the title.

        Example of conditions : {"id": 23, "level":2} will match the title that has id=23 and level=2

        Args:
            titles (Titles): the titles extracted from the text
            conditions (dict): dict of conditions, i.e key value paris that must exist in the title we look for
            raise_errors (bool, optional): raise error if more than 1 or less than 1 title is matched. Defaults to True.

        Raises:
            ChunkNorrisException: If not title matches the conditions
            ChunkNorrisException: If more than one title matches the conditions

        Returns:
            Title: The title that matches the conditions
        """
        conditions = list(conditions.items())
        title = [
            t
            for t in titles
            if all([condition in t.items() for condition in conditions])
        ]
        if raise_errors:
            if len(title) == 0:
                raise ChunkNorrisException(
                    f"No title matched conditions : {conditions}"
                )
            elif len(title) > 1:
                raise ChunkNorrisException(
                    f"More than 1 title matches conditions : {conditions} in\n{title}"
                )
        else:
            return title  # list of 0 to many titles

        return title[0]

    @staticmethod
    def get_direct_children_of_title(title: Title, titles: Titles) -> Titles:
        """Gets the direct children of a title, meaning
        the children without their children

        We assume that direct children have highest title level (closest to 0) among children

        Args:
            title (Title): the titles we want the children from

        Returns:
            Titles: the children titles
        """
        # if the title has no children, return empty list
        if not title["children"]:
            return []

        direct_children = [
            c
            for c in title["children"]
            if c["level"] == min(title["children"], key=lambda x: x["level"])["level"]
        ]

        return [
            MarkdownChunkNorris._get_title_using_condition(titles, c)
            for c in direct_children
        ]


    @staticmethod
    def _get_text_before_titles(titles:Titles) -> Titles:
        """Some documents may have text that arrives before any header.
        This function create a dummy title in the toc, at the very begining
        (like a parent of all titles) so that this text is taken into account

        Args:
            titles (Titles): the titles detected in the document
            text (str): the document's content
        """
        # insert new dummy title
        dummy_title = {
            "id": -1,
            "text": "",
            "level": -1,
            "start_position": -1,
            "end_position": -1,
                }
        titles.insert(0, dummy_title)

        return titles


    def get_chunks(self, titles: Titles, **kwargs) -> Chunks:
        """Builds the chunks based on the titles

        Args:
            titles (Titles): The titles, obtained from get_toc() method

        Returns:
            Chunks: a list of Chunk
        """
        text_chunks = MarkdownChunkNorris._get_chunks_text_content(titles, **kwargs)
        # Change position of links in the text
        text_chunks = [self.change_links_format(t, **kwargs) for t in text_chunks]
        # build list of chunks object
        chunks = []
        for i, text in enumerate(text_chunks):
            text = MarkdownChunkNorris.cleanup_text(text)
            chunks.append(
                {
                    "id": f"{i}",
                    "token_count": len(self.tokenizer.encode(text)),
                    "word_count": len(text.split()),
                    "text": text
                }
            )
        # check that chunks don't exceed the hard token limit
        chunks = self.check_chunks(chunks, **kwargs)

        return chunks

    @staticmethod
    def _get_chunks_text_content(
        titles: Titles,
        max_title_level_to_use: str = "h4",
        max_chunk_word_count: int = 250,
        **kwargs,
    ) -> list[str]:
        """Builds the chunks based on the titles obtained by the get_toc() method.

        It will split the text recursively using the titles. Here's what happens:
        - it takes a title and builds of chunk text (using title + content + content of children)
        - if the chunk obtained is too big and the title has children, it will subdivide it
        - otherwise the chunk is kept as is

        Note : titles that have a lower level that the one specified in max_title_level_to_use
        will not be considered for splitting

        Args:
            titles (Titles): The titles, obtained from get_toc() method
            max_title_level_to_use (str, optional): The lowest level of titles to consider.
                Defaults to "h4".
            max_chunk_word_count (int, optional): The max size a chunk can be. Defaults to 250.

        Returns:
            list[str]: the chunk's texts
        """
        MarkdownChunkNorris._check_string_argument_is_valid(
            "max_title_level_to_use",
            max_title_level_to_use,
            ["h1", "h2", "h3", "h4", "h5"],
        )

        total_chunks = []
        total_used_ids = []
        # make sure titles are sorted by order of appearance
        titles = sorted(titles, key=lambda x: x["start_position"])
        for title in titles:
            if title["id"] not in total_used_ids:
                chunk, used_ids = MarkdownChunkNorris._create_chunk(title, titles)
                # Note : we work on a lists to enable recursivity
                # if chunk is too big and but title can be subdivided using subsections...
                if MarkdownChunkNorris._chunk_is_too_big(
                    chunk, max_chunk_word_count
                ) and MarkdownChunkNorris._title_has_children(title, max_title_level_to_use):
                    titles_to_subdivide = [title]
                    # if the title has a content, create a chunk just with this title and its content
                    if title["content"]:
                        total_chunks.append(MarkdownChunkNorris.create_title_text(title))
                    total_used_ids.append(title["id"])
                # if chunk is OK, or too big but can't be subdivided with children...
                else:
                    titles_to_subdivide = []
                    total_chunks.append(chunk)
                    total_used_ids.extend(used_ids)
                # While we have chunks to subdivide, perform recursive subdivision
                while titles_to_subdivide:
                    new_titles_to_subdivide = []
                    for title2subdivide in titles_to_subdivide:
                        direct_children = MarkdownChunkNorris.get_direct_children_of_title(
                            title2subdivide, titles
                        )
                        for child in direct_children:
                            chunk, used_ids = MarkdownChunkNorris._create_chunk(
                                child, titles
                            )
                            if MarkdownChunkNorris._chunk_is_too_big(
                                chunk, max_chunk_word_count
                            ) and MarkdownChunkNorris._title_has_children(
                                child, max_title_level_to_use
                            ):
                                new_titles_to_subdivide.append(child)
                                if child["content"]:
                                    total_chunks.append(MarkdownChunkNorris.create_title_text(child))
                                total_used_ids.append(child["id"])
                            else:
                                total_chunks.append(chunk)
                                total_used_ids.extend(used_ids)

                    titles_to_subdivide = new_titles_to_subdivide

        return total_chunks

    @staticmethod
    def _chunk_is_too_big(chunk: str, max_chunk_length: int) -> bool:
        """Returns True if the chunk is bigger than the value
        specified as max_chunk_length in terms of word count

        Args:
            chunk (str): a chunk of text
            max_chunk_length (int): the max size of the chunk in words

        Returns:
            bool: True if the chunk is too big, else false
        """
        return len(chunk.split()) > max_chunk_length

    @staticmethod
    def _title_has_children(title: Title, max_title_level_to_use: str = "h4") -> bool:
        """Returns True if the title has children, ecluding title level
        that are lower than max_title_level_use

        Args:
            title (Title): the title to check for children
            max_title_level_to_use (str, optional): the max level of title to consider, included.
                Defaults to "h4".

        Returns:
            bool: True if the title has children
        """
        max_level = int(max_title_level_to_use[1]) - 1

        return bool([c for c in title["children"] if c["level"] <= max_level])

    @staticmethod
    def _create_chunk(title: Title, titles: Titles) -> tuple[str, list[int]]:
        """Creates a chunk, based on a title.
        A chunk is made from :
        - the title text
        - the content
        - the title text of its children
        - the content of its children
        - ... recursively for the children of children

        Args:
            title (Title): a title element
            titles (Titles): all the titles of the document

        Returns:
            tuple[str, list[int]]: Returns two things :
                - the chunk (as a string)
                - the list of ids of titles used to build the chunk
        """
        chunk = ""
        # add title text of parents + their content
        if title["parents"]:
            parents = sorted(title["parents"], key=lambda x: x["level"])
            for parent in parents:
                parent = MarkdownChunkNorris._get_title_using_condition(
                    titles, {"id": parent["id"]}
                )
                chunk += MarkdownChunkNorris.create_title_text(parent, with_content=False)
        # add title + content of current title
        chunk += MarkdownChunkNorris.create_title_text(title)
        used_titles_ids = [title["id"]]
        # add title + content of all children
        if title["children"]:
            for child in title["children"]:
                child = MarkdownChunkNorris._get_title_using_condition(
                    titles, {"id": child["id"]}
                )
                chunk += MarkdownChunkNorris.create_title_text(child)
                used_titles_ids.append(child["id"])

        return chunk, used_titles_ids

    @staticmethod
    def create_title_text(title: Title, with_content:bool=True) -> str:
        """Generate the text of the title, using the title name and 
        its content if 'with_content' is set tot True

        Args:
            title (Title): a title element
            with_content (bool): whether or not the title content should be added

        Returns:
            str: the text to put in the chunk for that title
        """
        title_text = ""
        # add # before title (markdown style)
        if title["text"]:
            title_text += "#" * (title["level"] + 1) + " " + title["text"] + "\n"
        # add title content
        if with_content:
            title_text += title["content"] + "\n" if title["content"] else ""

        return title_text

    def change_links_format(
        self, text, link_placement: str = "end_of_chunk", **kwargs
    ) -> str:
        """Removes the markdown format of the links in the text.
        The links are treated as specified by 'link_position':
        - remove : links are removed
        - in_sentence : the link is placed in the sentence, between parenthesis
        - end_of_chunk : all links are added at the end of the text
        - end_of_sentence : each link is added at the end of the sentence it is found in

        Args:
            text (str): the text to find the links in
            link_placement (str, optional): How the links should be handled. Defaults to end_of_chunk.

        Raises:
            NotImplementedError: _description_

        Returns:
            str: the formated text
        """
        allowed_link_placements = [
            "remove",
            "end_of_chunk",
            "in_sentence",
        ]
        MarkdownChunkNorris._check_string_argument_is_valid(
            "link_placement", link_placement, allowed_link_placements
        )

        image_pattern = re.compile(r'\[!\[([^\]]*)\]\((.*?)(?=\"|\))(\".*\")?\)\]\((https?:.+?)\)')
        image_matches = re.finditer(image_pattern, text)
        image_replacements = [(m[0], m[1], m[4]) for m in image_matches]
        if image_replacements is not None:
            text = MarkdownChunkNorris._handle_link_replacements(text, image_replacements, link_placement=link_placement)
      
        link_pattern = re.compile(r"\[(.+?)\]\((https?:.+?)\)")
        link_matches = re.finditer(link_pattern, text)
        link_replacements = [(m[0], m[1], m[2]) for m in link_matches]
        if link_replacements is not None:
            text = MarkdownChunkNorris._handle_link_replacements(text, link_replacements, link_placement=link_placement)      

        return text
    
    @staticmethod
    def _handle_link_replacements(text:str, replacements:list[tuple[str, str, str]], link_placement: str = "end_of_chunk") -> str:
        for i, m in enumerate(replacements):
            match link_placement:
                case "remove":
                    text = text.replace(m[0], m[1])
                case "end_of_chunk":
                    if i == 0:
                        text += "Pour plus d'informations:\n"
                    text = text.replace(m[0], m[1])
                    text += f"- {m[1]}: {m[2]}\n"
                case "in_sentence":
                    text = text.replace(
                        m[0], f"{m[1]} (pour plus d'informations : {m[2]})"
                    )
                
        return text

    def check_chunks(
        self,
        chunks: Chunks,
        min_chunk_word_count = 15,
        max_chunk_tokens: int = 8191,
        chunk_tokens_exceeded_handling: str = "raise_error",
        **kwargs,
    ):
        """Checks that the chunks do not exceed the token limit, considered as a hard limit
        If chunk_tokens_exceeded_handling is:
        - "raise_error" -> it will raise an error in case a chunk to big is found
        for it to be investigated.
        - "split" -> Chunks exceeding the max size will be split to fit max_chunk_tokens

        Args:
            chunks (Chunks): The chunks obtained from the get_chunks() method
            min_chunk_tokens (int, optional): the maximum size a chunk is allowed to be,
                in tokens. Defaults to 8191.
            chunk_tokens_exceeded_handling (str, optional): whether or not error sould be raised if a big
                chunk is encountered, or split. Defaults to raise_error.
        """
        MarkdownChunkNorris._check_string_argument_is_valid(
            "chunk_tokens_exceeded_handling",
            chunk_tokens_exceeded_handling,
            ["raise_error", "split"],
        )
        # remove small chunks
        chunks = [c for c in chunks if c["word_count"] > min_chunk_word_count]
        # split too big chunks
        splitted_chunks = []
        for chunk in chunks:
            if chunk["token_count"] < max_chunk_tokens:
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
                        splitted_chunk = self.split_big_chunk(chunk, max_chunk_tokens)
                        splitted_chunks.extend(splitted_chunk)

        return splitted_chunks

    def split_big_chunk(
        self,
        chunk: Chunk,
        max_chunk_tokens: int = 8191,
    ) -> Chunks:
        """Splits the chunk so that the subchunk fit un max_chunk_size

        Args:
            chunk (Chunk): _description_
            max_chunk_tokens (int, optional): _description_. Defaults to 8191.

        Returns:
            _type_: _description_
        """
        # if chunk is smaller that specified limit, just return the chunk
        if chunk["token_count"] < max_chunk_tokens:
            return [chunk]

        split_count = (chunk["token_count"] // max_chunk_tokens) + 1
        split_token_size = chunk["token_count"] // split_count
        # split the chunk's text
        tokenized_text = self.tokenizer.encode(chunk["text"])
        splitted_text = [
            self.tokenizer.decode(
                tokenized_text[i * split_token_size : (i + 1) * split_token_size]
            )
            for i in range(split_count)
        ]
        # recreate subchunks from the initial chunk
        splitted_chunk = [
            {
                "id": f"{chunk['id']}-{i}",
                "token_count": len(self.tokenizer.encode(sct)),
                "word_count": len(sct.split()),
                "text": sct,
            }
            for i, sct in enumerate(splitted_text)
        ]

        return splitted_chunk


