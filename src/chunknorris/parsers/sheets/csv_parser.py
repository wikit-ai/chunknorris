import csv
from io import StringIO
from typing import Literal

import pandas as pd

from ...core.components import MarkdownDoc
from .abstract_sheet_parser import AbstractSheetParser

_VALID_OUTPUT_FORMATS = ("markdown_table", "json_lines")


class CSVParser(AbstractSheetParser[str]):
    """Parser for Comma-Separated Values files (.csv)."""

    def __init__(
        self,
        csv_delimiter: str | None = None,
        output_format: Literal["markdown_table", "json_lines"] = "json_lines",
        n_sample_lines: int = 5,
    ) -> None:
        """Initializes a CSV parser.

        Args:
            csv_delimiter (str | None, optional): The delimiter used in the CSV file.
                If None, the delimiter is inferred automatically. Defaults to None.
            output_format (Literal["markdown_table", "json_lines"], optional): Output format.
                - markdown_table: renders the data as a Markdown table.
                - json_lines: each row is serialized as a JSON object on its own line.
                  Repeats column names on every row — more verbose but easier for LLMs.
                Defaults to "json_lines".
            n_sample_lines (int, optional): Number of lines sampled for delimiter detection.
                Only used when csv_delimiter is None. Defaults to 5.
        """
        if output_format not in _VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid value for argument 'output_format': expected one of "
                f"{list(_VALID_OUTPUT_FORMATS)}. Got '{output_format}'."
            )
        self.csv_delimiter = csv_delimiter
        self.output_format = output_format
        self.n_sample_lines = n_sample_lines

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Parses a CSV file to a MarkdownDoc.

        Args:
            filepath (str): path to the .csv file.

        Returns:
            MarkdownDoc: the parsed document.
        """
        if not filepath.lower().endswith(".csv"):
            raise ValueError("Only .csv files can be passed to CSVParser.")
        delimiter = self.csv_delimiter or self._detect_delimiter_from_file(
            filepath, self.n_sample_lines
        )
        df = pd.read_csv(filepath, delimiter=delimiter)  # type: ignore | missing typing in pandas
        return self._df_to_markdown_doc(df, self.output_format)

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a CSV-formatted string to a MarkdownDoc.

        Args:
            string (str): the CSV content as a string.

        Returns:
            MarkdownDoc: the parsed document.
        """
        delimiter = self.csv_delimiter or self._detect_delimiter_from_string(
            string, self.n_sample_lines
        )
        df = pd.read_csv(StringIO(string), delimiter=delimiter)  # type: ignore | missing typing in pandas
        return self._df_to_markdown_doc(df, self.output_format)

    @staticmethod
    def _detect_delimiter_from_file(filepath: str, n_sample_lines: int = 5) -> str:
        """Detect the CSV delimiter by reading the first few lines of a file.

        Args:
            filepath (str): path to the CSV file.
            n_sample_lines (int): number of lines to sample.

        Returns:
            str: the detected delimiter.

        Raises:
            ValueError: if the delimiter cannot be detected.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            sample = "".join(f.readline() for _ in range(n_sample_lines))
        return CSVParser._sniff_delimiter(sample)

    @staticmethod
    def _detect_delimiter_from_string(csv_string: str, n_sample_lines: int = 5) -> str:
        """Detect the CSV delimiter from a string sample.

        Args:
            csv_string (str): the CSV content as a string.
            n_sample_lines (int): number of lines to sample.

        Returns:
            str: the detected delimiter.

        Raises:
            ValueError: if the delimiter cannot be detected.
        """
        sample = "\n".join(csv_string.split("\n")[:n_sample_lines])
        return CSVParser._sniff_delimiter(sample)

    @staticmethod
    def _sniff_delimiter(sample: str) -> str:
        """Use csv.Sniffer to detect a delimiter from a string sample.

        Args:
            sample (str): a short excerpt of CSV content.

        Returns:
            str: the detected delimiter.

        Raises:
            ValueError: if detection fails.
        """
        try:
            return csv.Sniffer().sniff(sample).delimiter
        except csv.Error as e:
            raise ValueError(
                "Could not detect the CSV delimiter. Set it manually via "
                "CSVParser(csv_delimiter='<delimiter>')."
            ) from e
