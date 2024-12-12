import os
import logging
from tqdm import tqdm
from src.chunknorris.exceptions import TextNotFoundException, PageNotFoundException
from src.chunknorris.parsers import PdfParser
from src.chunknorris.pipelines import PdfPipeline
from src.chunknorris.chunkers import MarkdownChunker

# To run this test, use the following :
# python -m tests.test_scripts.test_on_all_pdf

# disable chunknorris logging INFO
logger = logging.getLogger()
logger.setLevel(level=logging.WARNING)

ROOT_DIR = r"C:\Users\mathi\Wikit\Data"

pdf_files: list[str] = []
for root, dirs, files in os.walk(ROOT_DIR):
    for file in files:
        if file.endswith(".pdf"):
            pdf_files.append(os.path.abspath(os.path.join(root, file)))

pipe = PdfPipeline(PdfParser(), MarkdownChunker())
pdf_with_errors: list[str] = []
for filepath in tqdm(pdf_files):
    try:
        chunks = pipe.chunk_file(filepath)
    except TextNotFoundException:
        print("No text found")
    except PageNotFoundException:
        print("No page found")
    except Exception as e:
        pdf_with_errors.append(filepath)
        raise e

print(f"Correct : {len(pdf_files) - len(pdf_with_errors)} / {len(pdf_files)} !")
if pdf_with_errors:
    print("Pdf files with errors:")
    for filepath in pdf_with_errors:
        print(filepath)
