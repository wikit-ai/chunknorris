import json

import nbformat

from chunknorris.parsers import JupyterNotebookParser
from chunknorris.core.components import MarkdownDoc


def test_parse_string(
    jupyter_notebook_parser: JupyterNotebookParser, jupyter_notebook_filepath: str
):
    # simply check it runs
    string = nbformat.writes(nbformat.read(jupyter_notebook_filepath, as_version=4))  # type: ignore
    assert isinstance(jupyter_notebook_parser.parse_string(string), MarkdownDoc)
    # it should also run using json.load()
    with open(jupyter_notebook_filepath, "r", encoding="utf8") as file:
        string = json.dumps(json.load(file))
    assert isinstance(jupyter_notebook_parser.parse_string(string), MarkdownDoc)


def test_parse_file(
    jupyter_notebook_parser: JupyterNotebookParser, jupyter_notebook_filepath: str
):
    parser_output = jupyter_notebook_parser.parse_file(jupyter_notebook_filepath)
    output_string = parser_output.to_string()
    assert isinstance(parser_output, MarkdownDoc)
    assert "content of markdown cell" in output_string
    assert "content of python cell" in output_string
    assert "content of javascript cell" in output_string
    assert "content of output cell" not in output_string
    # test with params
    jupyter_notebook_parser.include_code_cells_outputs = True
    parser_output = jupyter_notebook_parser.parse_file(jupyter_notebook_filepath)
    output_string = parser_output.to_string()
    assert "content of output cell" in output_string
