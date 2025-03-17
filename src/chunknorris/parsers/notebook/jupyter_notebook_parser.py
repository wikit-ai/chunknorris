import json
from pathlib import Path
from typing import Any

import nbformat
from pydantic import ValidationError

from ...core.components import MarkdownDoc
from ..abstract_parser import AbstractParser
from .schemas import JupyterNotebookContent


class JupyterNotebookParser(AbstractParser):
    """Class used to parse jupyter notebooks (.ipynb)."""

    def __init__(self, include_code_cells_outputs: bool = False) -> None:
        """Initializes the class.

        Args:
            include_code_cells_outputs (bool) : Whether or not the cells' output
                should be parsed as well. If False, they will be ignored. Default to False.
        """
        self.include_code_cells_outputs = include_code_cells_outputs

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Chunks a notebook .ipynb file.

        Args:
            filepath (str): the path to the file to parse.

        Returns:
            MarkDownDoc : the parsed markdown object.
        """
        file_content = self.read_file(filepath)
        md_string = self._parse_notebook_content(file_content)

        return MarkdownDoc.from_string(md_string)

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses the string considering it is a notebook content.

        Args:
            string (str): the string representing the notebook content. Assumed to be a dumped
                version of the JSON formatted notebook.

        Returns:
            MarkdownDoc: the formatted markdown document.
        """
        try:
            content = nbformat.reads(string, 4)  # type: ignore
            content = JupyterNotebookContent(**content)
        except ValidationError as e:
            raise e

        md_string = self._parse_notebook_content(content)

        return MarkdownDoc.from_string(md_string)

    @staticmethod
    def read_file(filepath: str) -> JupyterNotebookContent:
        """Reads a .ipynb file and returns its
        content as a json dict.

        Args:
            filepath (str): path to the file

        Returns:
            dict[str, Any]: the json content of the ipynb file
        """
        path = Path(filepath)
        if path.suffix != ".ipynb":
            raise ValueError(
                "Only .ipynb files can be passed to JupyterNotebookParser."
            )
        try:
            content = nbformat.read(filepath, 4)  # type: ignore
            content = JupyterNotebookContent(**content)
        except ValidationError as e:
            raise e

        return content

    def _parse_notebook_content(self, notebook_content: JupyterNotebookContent) -> str:
        """Parses the content of the notebook.

        Args:
            notebook_content (JupyterNotebookContent): the content of the notebook.

        Returns:
            str: the markdown string parsed from the notebook content
        """
        kernel_language = (
            notebook_content.metadata["language_info"]["name"]
            if notebook_content.metadata
            else ""
        )
        md_string = ""
        for cell in notebook_content.cells:
            match cell.cell_type:
                case "markdown" | "raw":
                    md_string += cell.source + "\n\n"
                case "code":
                    language = (
                        cell.metadata.get("vscode", {}).get("languageId", None)
                        or kernel_language
                    )
                    md_string += (
                        "```" + language + "\n" + "".join(cell.source) + "\n```\n\n"
                    )
                    if self.include_code_cells_outputs and cell.outputs:
                        md_string += (
                            "\n\n".join(
                                JupyterNotebookParser._parse_cell_output(output)
                                for output in cell.outputs
                            )
                            + "\n\n"
                        )

        return md_string

    @staticmethod
    def _parse_cell_output(cell_output: dict[str, Any]) -> str:
        """Parses a cell output to get a string from it.
        The format of a notebook's cell output's is described here : https://nbformat.readthedocs.io/en/latest/format_description.html#code-cell-outputs

        Args:
            cell_output (dict[str, Any]): a dictionnary representing a cell's output.

        Returns:
            str : the cell output as a string.
        """

        match cell_output["output_type"]:
            case "execute_result" | "display_data":
                text_output = ""
                for key, value in cell_output.get("data", {}).items():
                    if key == "application/json" or key.endswith("+json"):
                        text_output += json.dumps(value) + "\n\n"
                    elif key == "text/plain":
                        text_output += value + "\n\n"
                    elif key.startswith("image/"):
                        pass  # Do not include images as they are Base64 encoded ?
                return text_output.strip()
            case "stream":
                return cell_output["text"].strip()
            case _:
                pass
