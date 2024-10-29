import os
from tqdm import tqdm
from src.chunknorris.exceptions import TextNotFoundException, PageNotFoundException
from src.chunknorris.parsers import PdfParser
from src.chunknorris.pipelines import PdfPipeline
from src.chunknorris.chunkers import MarkdownChunker

ROOT_DIR = r"C:\Users\mathi\Wikit\Data"

pdf_files: list[str] = []
for root, dirs, files in os.walk(ROOT_DIR):
    for file in files:
        if file.endswith(".pdf"):
            pdf_files.append(os.path.abspath(os.path.join(root, file)))

pipe = PdfPipeline(PdfParser(), MarkdownChunker())
for filepath in tqdm(pdf_files):
    print(filepath)
    try:
        chunks = pipe.chunk_file(filepath)
    except TextNotFoundException:
        print("No text found")
    except PageNotFoundException:
        print("No page found")
