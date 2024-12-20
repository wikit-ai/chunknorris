import os
from chunknorris.parsers import AutoParser

def test_parse_file(dir_filepath: str):
    for file in os.listdir(dir_filepath):
        if file.endswith(".docx"): # Not handled so far. TODO : automatic method to check which files are handled
            continue
        if file.endswith(".json"): # files specific to wikit. Not included in AutoParser
            continue
        _ = AutoParser().parse_file(os.path.join(dir, file)) # must pass