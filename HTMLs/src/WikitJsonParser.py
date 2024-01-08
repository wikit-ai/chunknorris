import json
import os
import re
from typing import Dict, List 
from markdownify import markdownify


class WikitJsonParserException(Exception):
    def __init__(self, message):
        pass


class ChunkSizeExceeded(Exception):
    def __init__(self, message):
        pass


class WikitJsonParser:
    def __init__(self):
        pass

    
    def __call__(self, filepath:str, **kwargs) -> str:
        text = self.read_json_file(filepath)
        chunks = self.chunk_document(text, **kwargs)
        return chunks

    
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
            raise WikitJsonParserException(f"Can't open JSON file : {e}")

        return md_file


    @property
    def regex_patterns(self):
        return {
            "h1": re.compile(r"(.+?)\n={3,}"),
            "h2": re.compile(r"(.+?)\n-{3,}"),
            "h3": re.compile(r"### (.+)\n"),
            "h4": re.compile(r"#### (.+)\n"),
            "h5": re.compile(r"##### (.+)\n"),
            "link": re.compile(r"\[(.+?)\]\((https?:.+?)\)")
        }


    def get_toc(self, text:str) -> Dict:
        """Gets the table of content of the provided text.
        Parses the text to find headers, from h1 to h5.
        Handles specials cases, such as:
        - we have no header (-> returns empty dict)
        - we have a level missing (e.g. we have h1 and h3 but no h2)

        Args:
            text (str): the table of content, as a dict structured like so:
                {title: {
                    "level": the level (0-based),
                    "parents": the parent titles and their level,
                    "text": the text that is within this title
                    }}
        """
        def get_subtoc(text:str, level:int, parents:List[Dict], id_prefix:str):
            titles = re.findall(self.regex_patterns[f"h{level+1}"], text)
            text_splited_by_title = re.split(self.regex_patterns[f"h{level+1}"], text)
            text_splited_by_title = [t for t in text_splited_by_title if t not in titles]
            # remove first text if we found titles as it is before the first title. else keep the only element
            text_splited_by_title = text_splited_by_title[1:] if titles else text_splited_by_title
            toc = [
                {"title":t,
                "level": level,
                "text": txt,
                "id": f"{id_prefix}{i}",
                "parents": parents, 
                } for i, (t, txt) in enumerate(zip(titles, text_splited_by_title))]

            return titles, text_splited_by_title, toc


        def build_parents(toc:List[Dict], parent_ids:List[str]):
            assert isinstance(parent_ids, List), f"parent_titles shoud be a list, not {type(parent_ids)}"
            # remove Nones
            parent_ids = [t for t in parent_ids if not t.endswith("_")]
            # get the id of each parent title
            parent_titles = [
                WikitJsonParser.get_item(toc, conditions={"id": t})["title"]
                for t in parent_ids
                ]
            # build dict of parent titles
            parents = [{"level": i, "title": t, "id": tid}
                for i, (t, tid) in enumerate(zip(parent_titles, parent_ids))
                ]

            return parents


        def get_children(toc:Dict):
            # iterate through each element of toc
            for toc_piece in toc:
                children = []
                # reiterate through the toc to see if our toc_piece is in the parents of other to piceces
                for potential_child in toc:
                    parents = potential_child["parents"]
                    for p in parents:
                        if p["id"] == toc_piece["id"]:
                            children.append({
                                "level": potential_child["level"],
                                "title": potential_child["title"],
                                "id": potential_child["id"]
                                })
                toc_piece["children"] = children

            return toc

        h1_titles, h1_texts, toc = get_subtoc(text, 0, parents=[], id_prefix="0")
        for i, subtext_i in enumerate(h1_texts):
            h1_id = f"0{i}" if h1_titles else f"0_"
            parents = build_parents(toc, [h1_id])
            h2_titles, h2_texts, subtoc = get_subtoc(subtext_i, 1, parents=parents, id_prefix=h1_id)
            toc.extend(subtoc)
            for j, subtext_j in enumerate(h2_texts):
                h2_id = f"{h1_id}{j}" if h2_titles else f"{h1_id}_"
                parents = build_parents(toc, [h1_id, h2_id])
                h3_titles, h3_texts, subtoc = get_subtoc(subtext_j, 2, parents=parents, id_prefix=h2_id)
                toc.extend(subtoc)
                for k, subtext_k in enumerate(h3_texts):
                    h3_id = f"{h2_id}{k}" if h3_titles else f"{h2_id}_"
                    parents = build_parents(toc, [h1_id, h2_id, h3_id])
                    h4_titles, h4_texts, subtoc = get_subtoc(subtext_k, 3, parents=parents, id_prefix=h3_id)
                    toc.extend(subtoc)
                    for l, subtext_l in enumerate(h4_texts):
                        h4_id = f"{h3_id}{l}" if h4_titles else f"{h3_id}_"
                        parents = build_parents(toc, [h1_id, h2_id, h3_id, h4_id])
                        h5_titles, h5_texts, subtoc = get_subtoc(subtext_l, 4, parents=parents, id_prefix=h4_id)
                        toc.extend(subtoc)

        toc = get_children(toc)
        

        return toc


    @staticmethod
    def get_item(toc:List[Dict], conditions:Dict, return_attributes:List[str]=None, raise_errors=True):
        """Gets a toc element (=title) matching the specified condictions.
        'condictions' is a dict of conditions {key:value} -> we want to find
        the title in the toc that matches these conditions by having 
        these key-value pairs

        Args:
            toc (List[Dict]): the table of content
            conditions (Dict, optional): a dict of conditions to match. Defaults to Dict.
            raise_errors (bool, optional): if True, it will raise an error if the some keys in the condictions 
                can't be found in the toc element. Defaults to True.

        Raises:
            KeyError: _description_
            Exception: _description_
            Exception: _description_

        Returns:
            _type_: _description_
        """
        results = []
        for d in toc:
            if raise_errors and not all([k in d.keys() for k in conditions.keys()]):
                missing_keys = [k for k in conditions.keys() if k not in d.keys() ]
                raise KeyError(f"Some conditions specified can't be verified as the keys {missing_keys} are not present in dictionnary {d}")
                
            if all([d[k] == v for k, v in conditions.items() if k in d.keys()]):
                results.append(d)

        if len(results) > 1:
            raise Exception(f"More than one item corresponds to specified conditions: {conditions}. This should not happen. Items: {results}")
        if len(results) == 0:
            raise Exception(f"No item have been found corresponding to conditions : {conditions}")

        result = results[0]
        if return_attributes:
            return [result[a] for a in return_attributes]

        return result


    def chunk_document(self, text:str, max_chunk_size:int=300, chunk_on_title_level:int=None, raise_errors=True, **kwargs):
        """Chunks a document using titles
        The title level used to chunk can be forced by specifying chunk_on_title.
        Otherwise the each part will be chunk recursively using its titles until the chunks reach
        a size lower than the specified max_chunk_size.

        Args:
            text (str): _description_
            max_chunk_size (int, optional): _description_. Defaults to 300.
            chunk_on_title_level (int, optional): _description_. Defaults to None.
            raise_errors (bool, optional): _description_. Defaults to False.

        Raises:
            ChunkSizeExceeded: _description_

        Returns:
            _type_: _description_
        """
        # TODO: Handle case in which a portion of the text in a title is out of all its subtitles
        # For exemple the introduction of a part
        toc = self.get_toc(text)
        
        if chunk_on_title_level is not None:
            assert chunk_on_title_level in set(tp["level"] for tp in toc),\
            f"Can't chunk on level '{chunk_on_title_level}' as no title at that level are found"
            chunks = [self.format_chunk(tp) for tp in toc if tp["level"] == chunk_on_title_level]
            if any([len(c.split()) > max_chunk_size for c in chunks]) and raise_errors:
                raise ChunkSizeExceeded(f"Chunking on level '{chunk_on_title_level}' lead to oversized chunks")
        
        else:
            # Sort the titles by level (from lvl 0 to lvl 5)
            toc = sorted(toc, key=lambda x: x["level"])
            # store the toc parts that have been treated and the chunks
            treated_toc_ids = []
            total_chunks = []
            # iterate through each toc title
            for toc_piece in toc:
                # if this title have been already treated, then don't use it again
                if toc_piece["id"] in treated_toc_ids:
                    continue
                # build the chunk with the title we are using
                chunk = self.format_chunk(toc_piece)
                # check if the chunk is too big, if so subdivide it
                chunk_is_too_big = len(chunk.split()) > max_chunk_size
                if not chunk_is_too_big:
                    total_chunks.append(chunk)
                    treated_toc_ids.append(toc_piece["id"])
                    treated_toc_ids.extend([child["id"] for child in toc_piece["children"]])
                    toc_pieces_to_subdivide = []
                    continue
                else:
                    toc_pieces_to_subdivide = [toc_piece]
                # while we have toc pieces that needs to be subdivided...
                while toc_pieces_to_subdivide:
                    # ...iterate over the toc pieces that needs to be subdivided
                    for tp2subdivide in toc_pieces_to_subdivide:
                        # check if the tocpiece have children titles that we can use
                        if tp2subdivide["children"]:
                            children = []
                            for tpc in tp2subdivide["children"]:
                                child = WikitJsonParser.get_item(toc, conditions={"id": tpc["id"]})
                                child_id = child["id"]
                                children.append(child)
                                treated_toc_ids.append(child_id)
                            chunks = [self.format_chunk(child) for child in children]
                            toc_pieces_to_subdivide = [
                                child
                                for child, chunk in zip(children, chunks)
                                if len(chunk.split()) > max_chunk_size
                                ]
                            chunks_that_are_ok = [c for c in chunks if len(c.split()) < max_chunk_size]
                            total_chunks.extend(chunks_that_are_ok)
                        # if we don't have children (=subtitles) then just leave this a big chunk
                        # TODO: find other subdivision method for cases where we have no children titles
                        else:
                            toc_pieces_to_subdivide = []
                            treated_toc_ids.append(tp2subdivide["id"])
                            total_chunks.append(self.format_chunk(tp2subdivide))

        return total_chunks


    def format_chunk(self, toc_piece):
        chunk = ""
        if toc_piece["parents"]:
            chunk = "\n".join([WikitJsonParser.cleanup_text(p["title"]) for p in toc_piece["parents"]])
            chunk += "\n"
        chunk += f"{WikitJsonParser.cleanup_text(toc_piece['title'])}\n"
        chunk += WikitJsonParser.cleanup_text(toc_piece["text"])
        chunk = self.change_links_format(chunk, link_position="end_of_chunk")
        chunk += "\n"

        return chunk


    def change_links_format(self, text, link_position:str=None, **kwargs) -> str:
        """Removes the markdown format of the links in the text.
        The links are treated as specified by 'link_position':
        - None : links are removed
        - in_sentence : the link is placed in the sentence, between parenthesis
        - end_of_chunk : all links are added at the end of the text
        - end_of_sentence : each link is added at the end of the sentence it is found in

        Args:
            text (str): the text to find the links in
            link_position (str, optional): How the links should be handled. Defaults to None.

        Raises:
            NotImplementedError: _description_

        Returns:
            str: the formated text
        """
        matches = re.finditer(self.regex_patterns["link"], text)
        if matches is not None:
            for i, m in enumerate(matches):
                match link_position:
                    case None:
                        text = text.replace(m[0], m[1])
                    case "end_of_chunk":
                        if i == 0:
                            text += "\nPour plus d'informations:\n"
                        text = text.replace(m[0], m[1])
                        text += f"- {m[1]}: {m[2]}\n"
                    case "in_sentence":
                        text = text.replace(m[0], f"{m[1]} (pour plus d'informations : {m[2]})")
                    case "end_of_sentence":
                        link_end_position = m.span(2)[1]
                         #next_breakpoint = WikitJsonParser.find_end_of_sentence(text, link_end_position)
                        raise NotImplementedError

        return text


    @staticmethod
    def find_end_of_sentence(text, start_idx):
        next_breakpoint = text.find(".", start_idx)
        # if there is no ".", find \n
        if not next_breakpoint:
            next_breakpoint = text.find("\n", start_idx)
            # make sure this \n doesn't annouce a list, if so, go to next \n
            if text[next_breakpoint-1] == ":":
                next_breakpoint = text.find("\n", start_idx+3)
        # if we still don't have a breakpoint, then breakpoint is end of text
        if not next_breakpoint:
            next_breakpoint = len(text)

        return next_breakpoint


    @staticmethod
    def cleanup_text(text):

        # remove special characters
        text = text.replace("\xa0", "").replace("###", "")#.replace("–", "-")
        # remove strong markdown
        text = text.replace("**", "")
        # remove whitespaces and newlines
        text = " ".join(text.split())
        # restore newline for bullet-point lists
        text = "\n- ".join(text.split("- "))
        
        return text