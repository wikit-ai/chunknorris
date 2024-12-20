import os
from chunknorris.pipelines import AutoPipeline

def test_chunk_file(dir_filepath: str):
    for file in os.listdir(dir_filepath):
        if file.endswith(".docx"): # Not handled so far. TODO : automatic method to check which files are handled
            continue
        if file.endswith(".json"): # files specific to wikit. Not included in AutoParser
            continue
        _ = AutoPipeline().chunk_file(os.path.join(dir, file)) # must pass