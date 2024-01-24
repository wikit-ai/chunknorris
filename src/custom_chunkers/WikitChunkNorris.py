import os
import json
from argparse import ArgumentParser
from ..chunkers.HTMLChunkNorris import HTMLChunkNorris
from ..types.types import *


class WikitChunkNorris(HTMLChunkNorris):
    def __init__(self):
        super().__init__()

    def chunk_entire_directory(
        self, input_dir: str, output_dir: str = None, **kwargs
    ) -> None:
        """Chunks the json files of entire directory

        Args:
            input_dir (str): the path to directory
            output_dir (str): the directory where chunks will be saved
        """
        input_dir = os.path.normpath(input_dir)
        if not output_dir:
            output_dir = f"{input_dir}-chunked"
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
            with open(os.path.join(output_dir, fn), "w") as f:
                json.dump(file_content, f, ensure_ascii=False)

    @staticmethod
    def read_file(filepath: str, return_full_content: bool = False) -> str:
        """Reads a html or json file

        Args:
            filepath (str): path to a file. must end with .json or .html
            return_full_content (bool): Only applies to JSON files. Indicates whether or not
                the entire content of the file is returned or just the text content.
        Returns:
            str: the text, mardkownified
        """
        try:
            with open(filepath) as f:
                if filepath.endswith(".json"):
                    file = json.load(f)
                    if not return_full_content:
                        file = file["hasPart"][0]["text"]
                elif filepath.endswith(".html"):
                    file = f.read()
                else:
                    raise Exception(f"Can only open JSON or HTML files")
        except Exception as e:
            raise Exception(f"Can't open file '{filepath}': {e}")

        return file

    @staticmethod
    def format_output(filepath: str, chunks: Chunks) -> dict:
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
            }
            for i, c in enumerate(chunks)
        ]

        file_content["hasPart"] = chunks

        return file_content


def parse_arguments():
    """Parse the given command-line arguments."""

    parser = ArgumentParser(
        description="Chunking a folder of json files containing a HTML test under the key ['hasPart'][0]['text']"
    )

    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Path to folder containing the files to chunk",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Path to output folder where the chunked files will be stored",
    )
    parser.add_argument(
        "--max_title_level_to_use",
        type=str,
        choices=["h1", "h2", "h3", "h4", "h5"],
        default="h4",
        help="The maximum level of titles to use for chunking",
    )
    parser.add_argument(
        "--max_chunk_tokens",
        type=int,
        default=8191,
        help="Hard limit of the token size of a chunk. Chunks bigger than that will be handled according to chunk_tokens_exceeded_handling",
    )
    parser.add_argument(
        "--chunk_tokens_exceeded_handling",
        type=str,
        choices=["split", "raise_error"],
        default="raise_error",
        help="Whether a big chunk with not headers should be split or error should be raised",
    )
    parser.add_argument(
        "--link_placement",
        type=str,
        choices=["remove", "end_of_chunk", "in_sentence", "end_of_sentence"],
        default="end_of_chunk",
        help="Where the links are placed in the chunks",
    )
    parser.add_argument(
        "--max_chunk_word_count",
        type=int,
        default=250,
        help="Soft limit of chunk size. Chunks bigger than this limit will be subdivided with lower level headers.",
    )
    parser.add_argument(
        "--min_chunk_word_count",
        type=int,
        default=15,
        help="Minium amount a word a chunk must have. If lower, the chunk is discarded.",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    wcn = WikitChunkNorris()
    wcn.chunk_entire_directory(**dict(args._get_kwargs()))


if __name__ == "__main__":
    main()
