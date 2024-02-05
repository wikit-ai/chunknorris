
### WikitChunkNorris - custom chunker for wikit's json files

This chunker uses HTMLChunkNorris behind the scene but also has few ready to use methods ***especially for processing the JSON files obtained from our custom webscrapper*** (WordPress API).

In other words, the json file must have its html text content located at ```jsonfile["hasPart"][0]["text]```.

#### Usage

In order to chunk a json file :

```py
from custom_chunkers import WikitChunkNorris

wcn = WikitChunkNorris()
html_text = wcn.chunk_file("path_to_my_file.json")
```

Instead, if you wish to chunk ***an entire folder*** of json_files
```py
INPUT_FOLDER = "./my_folder_with_json_files/"
OUTPUT_FOLDER = "./my_empty_folder/"
wcn.chunk_directory(INPUT_FOLDER, OUTPUT_FOLDER)
```
If you do not specify the ``output_dir`` argument, files will be stored in a folder named ``<name_of_input_dir>-chunked`` by default.

Alternatively, if you cloned the repo, you can chunk a folder using the following command :
``python -m src.custom_chunkers.WikitChunkNorris --input_dir "<mydir>"``
Other arguments can be specified. For more information, check at **advanced usage of chunkers**.
