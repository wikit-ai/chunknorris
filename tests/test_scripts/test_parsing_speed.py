import json
import os
import sys
import time
from importlib.metadata import version

from tqdm import tqdm

from chunknorris.exceptions import TextNotFoundException
from chunknorris.parsers import PdfParser

DIR = "/Users/mathieu.ciancone/Wikit/Data/Miscelaneous/raw_pdfs"

VERSION = version("chunknorris") + "_pymupdf-v2.0"

filepaths = [
    os.path.join(DIR, filename)
    for filename in os.listdir(DIR)
    if filename.lower().endswith(".pdf")
]

user = input(
    f"Speed will be evaluated on {len(filepaths)} files and chunknorris version {VERSION}. Do you confirm ? [Y/n]"
)
if user.lower() == "n":
    sys.exit()

parser = PdfParser(use_ocr="never")

parsing_speeds: dict[str, float] = {}
for i, fp in enumerate(tqdm(filepaths)):
    filename = os.path.basename(fp)
    try:
        start = time.perf_counter()
        _ = parser.parse_file(fp)
        duration = time.perf_counter() - start
        parsing_speeds[filename] = duration

    except TextNotFoundException:
        pass

    except Exception as e:
        print("Error when parsing", filename, "\n", e)

try:
    with open("tests/test_scripts/parsing_speeds_refs.json", "r") as file:
        runs = json.load(file)
except:
    runs = {}

runs = {VERSION: parsing_speeds}
with open("parsing_speeds_refs.json", "w", encoding="utf-8") as file:
    json.dump(runs, file, indent=4, ensure_ascii=False)
