import os
from argparse import ArgumentParser

from .chunkers import MarkdownChunker
from .core.logger import LOGGER
from .parsers import DocxParser, HTMLParser, MarkdownParser, PdfParser, WikitJsonParser
from .pipelines import BasePipeline, WikitJsonPipeline


def parse_arguments():
    """Parse the given command-line arguments."""

    parser = ArgumentParser(description="Tool meant to chunk the content of a file")
    parser.add_argument(
        "--filepath",
        type=str,
        required=True,
        help="Path to the file to chunk",
    )
    parser.add_argument(
        "--max_headers_to_use",
        type=str,
        choices=["h1", "h2", "h3", "h4", "h5"],
        default="h4",
        help="The maximum level of titles to use for chunking",
    )
    parser.add_argument(
        "--max_chunk_word_count",
        type=int,
        default=250,
        help="Soft limit of chunk size (in words). Chunks bigger than this limit will be subdivided with lower level headers if available.",
    )
    parser.add_argument(
        "--hard_max_chunk_word_count",
        type=int,
        default=400,
        help="Hard limit of chunk size (in words). Chunks bigger than that will be subdivided so that each subchunk has less words than specified value.",
    )
    parser.add_argument(
        "--min_chunk_word_count",
        type=int,
        default=15,
        help="Minium amount a word a chunk must have. If lower, the chunk is discarded.",
    )
    parser.add_argument(
        "--remove_links",
        type=bool,
        default=False,
        help="Whether or not the links should be removed.",
    )
    parser.add_argument(
        "--use_ocr",
        type=str,
        choices=["auto", "never", "always"],
        default="auto",
        help="For PDF only : whether or not OCR should be used.",
    )
    parser.add_argument(
        "--ocr_language",
        type=str,
        default="fra+eng",
        help='For PDF only : the languages to consider for OCR. Must be a string of 3 letter codes languages separated by "+", such as "eng+fra"',
    )
    parser.add_argument(
        "--extract_tables",
        type=bool,
        default=True,
        help="For PDF only : whether or not tables should be extracted",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    filename, fileext = os.path.splitext(args.filepath)

    chunker = MarkdownChunker(
        max_headers_to_use=args.max_headers_to_use,
        max_chunk_word_count=args.max_chunk_word_count,
        hard_max_chunk_word_count=args.hard_max_chunk_word_count,
        min_chunk_word_count=args.min_chunk_word_count,
    )

    LOGGER.info("Chunking...")

    match fileext:
        case ".md":
            parser = MarkdownParser()
            pipeline = BasePipeline(parser, chunker)
        case ".html":
            parser = HTMLParser()
            pipeline = BasePipeline(parser, chunker)
        case ".pdf":
            parser = PdfParser(
                extract_tables=args.extract_tables,
                ocr_language=args.ocr_language,
                use_ocr=args.use_ocr,
            )
            pipeline = BasePipeline(parser, chunker)
        case ".docx":
            parser = DocxParser()
            pipeline = BasePipeline(parser, chunker)
        case ".json":
            parser = WikitJsonParser()
            pipeline = WikitJsonPipeline(parser, chunker)
        case _:
            raise ValueError(
                "ChunkNorris currently only supports .md, .html, .pdf, .docx and .json files."
            )

    chunks = pipeline.chunk_file(filepath=args.filepath)
    LOGGER.info("%i obtained !", len(chunks))

    args.output_filename = filename + "-chunks.json"
    pipeline.save_chunks(chunks, args.output_filename, args.remove_links)
    LOGGER.info("Chunks saved at %s", args.output_filename)


if __name__ == "__main__":
    main()
