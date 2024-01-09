import json
import re
from typing import Dict, List, Tuple, TypedDict
from markdownify import markdownify


# Types
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
    content:str
    parents: List[ShortTitle]
    children: List[ShortTitle]
    
Titles = List[Title]


class HTMLChunkNorrisException(Exception):
    def __init__(self, message):
        pass


class ChunkSizeExceeded(Exception):
    def __init__(self, message):
        pass


class HTMLChunkNorris:
    def __init__(self):
        pass

    
    def __call__(self, filepath:str, **kwargs) -> str:
        text = HTMLChunkNorris.read_json_file(filepath)
        titles = self.get_toc(text, **kwargs)
        chunks = HTMLChunkNorris.get_chunks(titles, **kwargs)

        return chunks
    
    
    @property
    def regex_patterns(self):
        return {
            "h1": re.compile(r"(.+?)\n={3,}", re.MULTILINE),
            "h2": re.compile(r"(.+?)\n-{3,}", re.MULTILINE),
            "h3": re.compile(r"^#{3} (.+)\n", re.MULTILINE),
            "h4": re.compile(r"^#{4} (.+)\n", re.MULTILINE),
            "h5": re.compile(r"^#{5} (.+)\n", re.MULTILINE),
            "link": re.compile(r"\[(.+?)\]\((https?:.+?)\)")
        }


    @staticmethod
    def read_json_file(filepath:str) -> str:
        """Reads a json file and applies markdownify to it

        Args:
            filepath (str): path to a json file

        Returns:
            str: the text, mardkownified
        """
        try:
            with open(filepath, 'r') as f:
                read_file = json.load(f)
            md_file = markdownify(read_file["hasPart"][0]['text'], strip=["figure", "img"], bullets="-*+")
        except Exception as e:
            raise HTMLChunkNorrisException(f"Can't open JSON file : {e}")

        return md_file
    
    
    def get_toc(self, text:str) -> Titles:
        """Get the Table Of Content i.e the list
        of titles and their relation with each other

        Args:
            text (str): the text to get the toc from

        Returns:
            Titles: list of dicts describing the titles. For more info, look at Title class
        """
        titles = self.get_titles(text)
        titles = HTMLChunkNorris.get_titles_children(titles)
        titles = HTMLChunkNorris.get_titles_parents(titles)
        titles = HTMLChunkNorris.get_titles_content(titles, text)

        return titles
    

    def get_titles(self, text:str, max_title_level:str="h4") -> Titles:
        """Gets the titles (=headers h1, h2 ...) in the text
        using regex

        Args:
            text (str): the titles to look for titles in
            max_title_level (str, optional): the max level of headers to look for (included). Defaults to "h4".

        Returns:
            Titles: a list of dicts describing titles. For more info, look at Title class
        """
        # Get the titles types to consider (h1, h2, ...)
        title_types_to_consider = [f"h{i}" for i in range(1, int(max_title_level[1])+1)]
        titles = []
        for title_level, title_type in  enumerate(title_types_to_consider):
            regex_pattern = self.regex_patterns[title_type]
            for match in re.finditer(regex_pattern, text):
                title_text = match.group(1)
                start_position = match.start()
                end_position = match.end()
                titles.append({"text": title_text, "level": title_level, "start_position": start_position, "end_position": end_position})

        # add id to each title
        titles = [{"id": i} | title for i, title in enumerate(titles)]
        
        return titles
    

    @staticmethod
    def get_titles_content(titles:Titles, text:str) -> Titles:
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
                next_title = titles[i+1]
                content = text[title["end_position"]: next_title["start_position"]]
            else: # its the last title
                content = text[title["end_position"]:]
            title["content"] = HTMLChunkNorris.cleanup_text(content)

        return titles


    @staticmethod
    def cleanup_text(text:str) -> str:
        """Cleans up a text using various operations

        Args:
            text (str): the text to cleanup

        Returns:
            str: the cleanedup text
        """
        # remove special characters
        special_chars = ["**", "\xa0"]
        for char in special_chars:
            text = text.replace(char, "")
        # remove white spaces and newlines
        text = " ".join(text.split())
        # restore newline for bullet-point lists
        text = "\n- ".join(text.split("- "))

        return text


    @staticmethod
    def get_titles_children(titles:Titles) -> Titles:
        """For each title, gets its children titles,
        meaning the titles of its subsections.

        A child is:
         - after in terms of position (higher 'start_position')
         - lower in terms of level (higher 'level')

        Args:
            titles (Titles): The titles found in the text

        Returns:
            Titles: The titles, with "children" fields added
        """
        # in the children, put the titles without their "content", "children" or "parents" fields
        child_keys_to_keep = ["id", "text", "level", "start_position", "end_position"]
        for title in titles:
            title_of_next_section = HTMLChunkNorris.get_title_of_next_section(title, titles)
            if title_of_next_section is None:
                title["children"] = [
                    {k:v for k,v in t.items() if k in child_keys_to_keep}
                    for t in titles
                    if t["start_position"] > title["end_position"]
                    ]
            else:
                title["children"] = [
                    {k:v for k,v in t.items() if k in child_keys_to_keep}
                    for t in titles
                    if t["start_position"] > title["end_position"]
                    and t["end_position"] < title_of_next_section["start_position"]
                    ]

        return titles


    @staticmethod
    def get_titles_parents(titles:Titles) -> Titles:
        """Gets the parents of each title

        Parents are titles of the section that a title 
        belongs to.

        Args:
            titles (Titles): The titles found in the text

        Returns:
            Titles: the titles with "parents" section added
        """
        # in the parents, put the titles without their "content", "children" or "parents" fields
        parent_keys_to_keep = ["id", "text", "level", "start_position", "end_position"]
        for title in titles:
            parents = []
            # find the title's parent, and consecutive parents of parents
            direct_parent = title
            while direct_parent:
                direct_parent = HTMLChunkNorris.get_direct_parent_of_title(direct_parent, titles)
                if direct_parent is not None:
                    direct_parent = {k:v for k,v in direct_parent.items()
                                     if k in parent_keys_to_keep}
                    parents.append(direct_parent)
            title["parents"] = parents

        return titles


    @staticmethod
    def get_direct_parent_of_title(title:Title, titles:Titles) -> Title:
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
            t for t in titles
            if t["level"] < title["level"]
            and t["end_position"] < title["start_position"]
            ]
        if not direct_parent:
            return None
        
        return max(direct_parent, key=lambda x: x["start_position"])
    

    @staticmethod
    def get_title_of_next_section(title:Title, titles:Titles) -> Title:
        """Considering a title, gets the title of the next section.
        The next section comes when we reach a title that as a
        equal or higher level than the provided title.

        Example: considering a h3, the next section's title would be when
        we encounter an other h3 or h2 or h1

        WARNING: May return None if no next section's title is found

        Args:
            title (Title): The title that we consider
            titles (Titles): List of titles of the document

        Returns:
            Title: The title of next section
        """
        same_level_titles = [
            t for t in titles
            if t["level"] <= title["level"]
            and t["start_position"] > title["end_position"]
            ]
        # if we have no next sections's title
        if not same_level_titles:
            return None
        
        return min(same_level_titles, key=lambda x: x["start_position"])
    

    @staticmethod
    def get_title_of_next_subsection(title:Title, titles:Titles) -> Title:
        """Considering a title, gets the title of the next subsection.
        The next subsection comes when we reach a title that as a
        lower level than the provided title.

        Example: considering a h3, the next section's title would be when
        we encounter an other h4 or h5

        WARNING: May return None if no next section's title is found

        Args:
            title (Title): The title that we consider
            titles (Titles): List of titles of the document

        Returns:
            Title: The title of next section
        """
        same_level_titles = [
            t for t in titles
            if t["level"] > title["level"]
            and t["start_position"] > title["end_position"]
            ]
        # if we have no next sections's title
        if not same_level_titles:
            return None
        
        return min(same_level_titles, key=lambda x: x["start_position"])
    

    @staticmethod
    def get_title_using_condition(titles:Titles, conditions:Dict, raise_errors:bool=True) -> Title:
        """Get the titles corresponding to the conditions.
        The conditions must be a dict. The method check that the keys-values pairs of conditions
        exist in the title.

        Example of conditions : {"id": 23, "level":2} will match the title that has id=23 and level=2 

        Args:
            titles (Titles): the titles extracted from the text
            conditions (Dict): dict of conditions, i.e key value paris that must exist in the title we look for
            raise_errors (bool, optional): raise error if matched title is not exaclty 1. Defaults to True.

        Raises:
            HTMLChunkNorrisException: If not title matches the conditions
            HTMLChunkNorrisException: If more than one title matches the conditions

        Returns:
            Title: The title that matches the conditions
        """

        conditions = list(conditions.items())
        title = [t for t in titles
                if all([condition in t.items() for condition in conditions])]
        if raise_errors:
            if len(title) == 0:
                raise HTMLChunkNorrisException(f"No title matched conditions : {conditions}")
            elif len(title) > 1:
                raise HTMLChunkNorrisException(f"More than 1 title matches conditions : {conditions} in\n{title}")
        else:
            return title # list of 0 to many titles
        
        return title[0]
    

    @staticmethod
    def get_direct_children_of_title(title:Title, titles:Titles) -> Titles:
        """Gets the directs children of a title, meaning
        the children without their children

        We assume that direct children have highest title level (closest to 0) among children

        Args:
            title (Title): the titles we want the children from

        Returns:
            Titles: the children titles
        """
        # if the title has no children, return empty list
        if not title["children"]:
            return   []
        
        direct_children = [
            c for c in title["children"]
            if c["level"] == min(title["children"], key=lambda x: x["level"])["level"]
            ]
        
        return [HTMLChunkNorris.get_title_using_condition(titles, c)
                for c in direct_children]
        
    
    @staticmethod
    def get_chunks(titles:Titles, max_title_level_to_use:str="h4", max_chunk_word_length:int=250) -> List[str]:
        """Builds the chunks based on the titles obtained by the get_toc() method.

        It will split the text recursively using the titles. Here's what happens:
        - it takes a title and builds of chunk with the title, its content, and the content of its children
        - if the chunk obtained is too big and the title has children, it will subdivide it
        - otherwise the chunk is kept as is

        Note : titles that have a lower level that the one specified in max_title_level_to_use
        will not be considered for splitting

        Args:
            titles (Titles): The titles, obtained from get_toc() method
            max_title_level_to_use (str, optional): The lowest level of titles to consider.
                Defaults to "h4".
            max_chunk_word_length (int, optional): The max size a chunk can be. Defaults to 250.

        Returns:
            List[str]: the chunk's texts
        """
        assert max_title_level_to_use in ["h1", "h2", "h3", "h4", "h5"],\
            ValueError(f"Argument 'max_title_level_to_use' should be one of ['h1', 'h2', 'h3', 'h4', 'h5']. Got '{max_title_level_to_use}'")
        total_chunks = []
        total_used_ids = []
        # make sure titles are sorted by order of appearance
        titles = sorted(titles, key=lambda x: x["start_position"])
        for title in titles:
            if title["id"] not in total_used_ids:
                chunk, used_ids = HTMLChunkNorris.create_chunk(title, titles)
                # Note : we work on a lists to enable recursivity
                # if chunk is too big and but title can be subdivide (because they have children)
                if HTMLChunkNorris.chunk_is_too_big(chunk, max_chunk_word_length)\
                and HTMLChunkNorris.title_has_children(title, max_title_level_to_use):
                    titles_to_subdivide = [title]
                    total_used_ids.append(title["id"])
                # if chunk is OK, or too big but can't be subdivided with children
                else:
                    titles_to_subdivide = []
                    total_chunks.append(chunk)
                    total_used_ids.extend(used_ids)
                # While we have chunks to subdivide, recursive subdivision
                while titles_to_subdivide:
                    new_titles_to_subdivide = []
                    for title2subdivide in titles_to_subdivide:
                        direct_children = HTMLChunkNorris.get_direct_children_of_title(title2subdivide, titles)
                        for child in direct_children:
                            chunk, used_ids = HTMLChunkNorris.create_chunk(child, titles)
                            if HTMLChunkNorris.chunk_is_too_big(chunk, max_chunk_word_length)\
                            and HTMLChunkNorris.title_has_children(child, max_title_level_to_use):
                                new_titles_to_subdivide.append(child)
                                total_used_ids.append(child["id"])
                            else:
                                total_chunks.append(chunk)
                                total_used_ids.extend(used_ids) 

                    titles_to_subdivide = new_titles_to_subdivide

        return total_chunks


    @staticmethod
    def chunk_is_too_big(chunk:str, max_chunk_length:int) -> bool:
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
    def title_has_children(title:Title, max_title_level_to_use:str="h4") -> bool:
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
    def create_chunk(title:Title, titles:Titles) -> Tuple[str, List[int]]:
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
            Tuple[str, List[int]]: Returns two things :
                - the chunk (as a string)
                - the list of ids of titles used to build the chunk
        """
        chunk = ""
        # add title text of parents + their content
        if title["parents"]:
            parents = sorted(title["parents"], key=lambda x: x["level"])
            for parent in parents:
                parent = HTMLChunkNorris.get_title_using_condition(titles, {"id": parent["id"]})
                chunk += HTMLChunkNorris.create_title_text(parent)
        # add title + content of current title
        chunk += HTMLChunkNorris.create_title_text(title)
        used_titles_ids = [title["id"]]
        # add title + content of all children
        if title["children"]:
            for child in title["children"]:
                child = HTMLChunkNorris.get_title_using_condition(titles, {"id": child["id"]})
                chunk += HTMLChunkNorris.create_title_text(child)
                used_titles_ids.append(child["id"])

        return chunk, used_titles_ids


    @staticmethod
    def create_title_text(title:Title) -> str:
        """Generate the text of the title, using the title name and it's content

        Args:
            title (Title): a title element

        Returns:
            str: the text to put in the chunk for that title
        """
        # add # before title (markdown style)
        title_text = "#" * (title["level"] + 1) + " " + title["text"] + "\n"
        # add title content
        title_text += title["content"] + "\n" if title["content"] else "" 
        
        return title_text