import os
import json
from ..chunkers.HTMLChunkNorris import HTMLChunkNorris
from ..types.types import *

# specify working dir
# os.chdir(os.path.dirname(os.path.abspath(__file__)))

class WikitChunkNorris(HTMLChunkNorris):
    def __init__(self):
        super().__init__()
    

    def chunk_entire_directory(self, input_dir:str, output_dir:str, **kwargs) -> None:
        """Chunks the json files of entire directory

        Args:
            input_dir (str): the path to directory
            output_dir (str): the directory where chunks will be saved
        """
        if os.path.exists(output_dir) and os.listdir(output_dir):
            raise ValueError("Output directory already contains data !")
        elif not os.path.exists(output_dir):
            os.mkdir(output_dir)

        filenames = os.listdir(input_dir)
        for fn in filenames:
            filepath = os.path.join(input_dir, fn)
            html_text = WikitChunkNorris.read_file(filepath)
            chunks = self.__call__(html_text, **kwargs)
            file_content = WikitChunkNorris.format_output(filepath, chunks)
            with open(os.path.join(output_dir, fn), "w", encoding="utf8") as f:
                json.dump(file_content, f, ensure_ascii=False)


    @staticmethod
    def read_file(filepath: str, return_full_content:bool=False) -> str:
        """Reads a html or json file

        Args:
            filepath (str): path to a file. must end with .json or .html
            return_full_content (bool): Only applies to JSON files. Indicates whether or not
                the entire content of the file is returned or just the text content.
        Returns:
            str: the text, mardkownified
        """
        try:
            with open(filepath, "r") as f:
                if filepath.endswith(".json"):
                    file = json.load(f)
                    if not return_full_content:
                        file = file["hasPart"][0]["text"]
                elif filepath.endswith(".html"):
                    file = f.read()
                else:
                    raise Exception(f"Can only open JSON or HTML files")
        except Exception as e:
            raise Exception(f"Can't open file : {e}")

        return file
    

    @staticmethod
    def format_output(filepath:str, chunks:Chunks) -> dict:
        """Formats the chunks according to the input json file
        i.e places the chunks inside the key [hasPart]

        Args:
            filepath (str): path toward the json file
            chunks (Chunks): the chunks

        Returns:
            dict: the formatted file content
        """
        file_content = WikitChunkNorris.read_file(filepath, return_full_content=True)
        chunks = [
            {
                "@type": "DocumentChunk", 
                "text": c["text"],
                "position": i,
            } for i, c in enumerate(chunks)]
        
        file_content["hasPart"] = chunks

        return file_content