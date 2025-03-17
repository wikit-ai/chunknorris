import glob
import json
import os
from argparse import ArgumentParser

from ..chunkers.markdown_chunker import MarkdownChunker
from ..core.components import Chunk
from ..decorators.decorators import validate_args
from ..parsers.json.wikit_parser import WikitJsonParser
from ..schemas.schemas import WikitJSONDocument, WikitJSONDocumentChunk


class WikitJsonPipeline:
    parser: WikitJsonParser
    chunker: MarkdownChunker

    @validate_args
    def __init__(self, parser: WikitJsonParser, chunker: MarkdownChunker) -> None:
        self.parser = parser
        self.chunker = chunker

    def chunk_file(self, filepath: str) -> list[Chunk]:
        """Chunks a json file formatted
        according to wikit's schema.

        Args:
            filepath (str): the path to the json file.

        Returns:
            list[Chunk]: the list of chunks
        """
        parsed_md = self.parser.parse_file(filepath)
        return self.chunker.chunk(parsed_md)

    def chunk_string(self, string: str) -> list[Chunk]:
        """Chunks a json string formatted according to
        wikit's schema.

        Args:
            string (str): the json string, obtained
                by using json.dumps() for the file.

        Returns:
            list[Chunk]: the list of chunks
        """
        parsed_md = self.parser.parse_string(string)
        return self.chunker.chunk(parsed_md)

    def chunk_and_save(self, filepath: str, output_filepath: str | None = None) -> None:
        """Chunks the file and saves the chunks
        in the WikiJsonDocument format.

        Args:
            filepath (str): the path to the json file.
            output_filepath (str): the path of the output json.
        """
        if not output_filepath:
            output_filepath = filepath.replace(".json", "-chunked.json")
        json_content = self.parser.read_file(filepath)
        md_lines = self.parser.parse_wikit_json_document(json_content)
        chunks = self.chunker.chunk(md_lines)
        json_content.has_part = self._format_chunks(chunks)
        self._save_content_as_wikit_json(json_content, output_filepath)

    def chunk_directory(self, input_dir: str) -> None:
        """Chunks the json files of entire directory, recursively

        Args:
            input_dir (str): the path to directory
        """
        if not os.path.isdir(input_dir) and os.path.exists(input_dir):
            raise ValueError("input_dir must point to an existing directory.")

        output_dir = os.path.dirname(input_dir) + "-chunked"

        filepaths: list[str] = [
            subdir
            for dir in os.walk(input_dir)
            for subdir in glob.glob(os.path.join(dir[0], "*.json"))
        ]

        for filepath in filepaths:
            output_filepath = filepath.replace(input_dir, output_dir)
            self.chunk_and_save(filepath, output_filepath)

    def _save_content_as_wikit_json(
        self, content: WikitJSONDocument, out_filepath: str
    ) -> None:
        """Saves each chunk in a MarkDown file.

        Args:
            out_filepath (str): the path where to save the output
            json_content (dict): the content of the json to save.
        """
        output_dir = os.path.dirname(out_filepath)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(out_filepath, "w", encoding="utf-8") as file:
            json.dump(content.model_dump(), file, ensure_ascii=False, indent=4)

    def _format_chunks(self, chunks: list[Chunk]) -> list[WikitJSONDocumentChunk]:
        """Formats the chunks according to the input json file
        i.e places the chunks inside the key [hasPart]

        Args:
            json_content (dict): the json content of the source json file. Obtained from
                read_file().
            chunks (Chunks): the chunks obtained.

        Returns:
            dict: the formatted file content
        """
        has_part = [
            WikitJSONDocumentChunk(type="DocumentChunk", text=chunk.get_text(), position=i)  # type: ignore : known problem where pydantic looks for @type instead of type. see https://github.com/pydantic/pydantic/issues/4936
            for i, chunk in enumerate(chunks)
        ]

        return has_part

    def save_chunks(
        self, chunks: list[Chunk], output_filename: str, remove_links: bool = False
    ) -> None:
        """Saves the chunks at the designated location
        as a json list of chunks.

        Args:
            chunks (Chunks): the chunks.
            output_filename (str): the JSON file where to save the files. Must be json.
            remove_links (bool): Whether or not links should be remove from the chunk's text content.
        """
        self.chunker.save_chunks(chunks, output_filename, remove_links)


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
        "--max_headers_to_use",
        type=str,
        choices=["h1", "h2", "h3", "h4", "h5"],
        default="h4",
        help="The maximum level of headers to use for chunking",
    )
    parser.add_argument(
        "--hard_max_chunk_word_count",
        type=int,
        default=400,
        help="Hard limit of the size of a chunk (in words).",
    )
    parser.add_argument(
        "--remove_links",
        type=bool,
        default=False,
        help="Whether or not the links should be removed.",
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

    parser = WikitJsonParser()
    chunker = MarkdownChunker(
        max_headers_to_use=args.max_headers_to_use,
        max_chunk_word_count=args.max_chunk_word_count,
        hard_max_chunk_word_count=args.hard_max_chunk_word_count,
        min_chunk_word_count=args.min_chunk_word_count,
    )
    pipeline = WikitJsonPipeline(parser=parser, chunker=chunker)
    pipeline.chunk_directory(args.input_dir)


if __name__ == "__main__":
    main()
