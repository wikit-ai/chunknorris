import logging
import os
from argparse import ArgumentParser

from tqdm import tqdm

from src.chunknorris.chunkers import MarkdownChunker
from src.chunknorris.exceptions import PageNotFoundException, TextNotFoundException
from src.chunknorris.parsers import PdfParser, DocxParser
from src.chunknorris.pipelines import PdfPipeline, BasePipeline

# To run this test, use the following :
# python -m tests.test_scripts.test_on_all_files --file_type pdf

argparser = ArgumentParser(
    description="Tools to test the package on a specific file type."
)
argparser.add_argument(
    "--file_type",
    type=str,
    choices=["pdf", "docx"],
    required=True,
    help="The type of file format to run the test on.",
)
argparser.add_argument(
    "--files_dir",
    type=str,
    default=r"C:\Users\mathi\Wikit\Data",
    help="The type of file format to run the test on.",
)
args = argparser.parse_args()

# disable chunknorris logging INFO
logger = logging.getLogger()
logger.setLevel(level=logging.WARNING)


file_to_test: list[str] = []
for root, dirs, files in os.walk(args.files_dir):
    for file in files:
        if file.endswith(f".{args.file_type}"):
            file_to_test.append(os.path.abspath(os.path.join(root, file)))

match args.file_type:
    case "pdf":
        parser = PdfParser(
            use_ocr="never",
            extract_tables=True,
        )
        pipe = PdfPipeline(parser, MarkdownChunker())
    case "docx":
        pipe = BasePipeline(DocxParser(), MarkdownChunker())
    case _:
        raise ValueError("Only .pdf and .docx file are handled.")

file_with_errors: list[str] = []
for filepath in tqdm(file_to_test):
    try:
        chunks = pipe.chunk_file(filepath)
    except TextNotFoundException:
        print("No text found")
    except PageNotFoundException:
        print("No page found")
    except Exception as e:
        print(filepath)
        file_with_errors.append(filepath)
        raise e

print(f"Correct : {len(file_to_test) - len(file_with_errors)} / {len(file_to_test)} !")
if file_with_errors:
    print("Files leading to errors:")
    for filepath in file_with_errors:
        print(filepath)
