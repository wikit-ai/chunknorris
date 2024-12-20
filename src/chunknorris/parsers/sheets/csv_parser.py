import csv

import pandas as pd

from ..abstract_parser import AbstractParser
from ..markdown.components import MarkdownDoc


class CSVParser(AbstractParser):
    """Parser for Comma-Separated Values file (.csv)"""

    def __init__(self, csv_delimiter: str | None = None) -> None:
        """Initializes a sheet parser

        Args:
            csv_delimiter (str | None, optional): The delimiter to consider to parse the .csv files.
                If None, we will try to guess what the delimiter is. Defaults to None.
        """
        self.csv_delimiter = csv_delimiter

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Parses a csv file to markdown.

        Args:
            filepath (str): the path to the csv file.

        Returns:
            MarkdownDoc: the markdown-formatted csv.
        """
        df = self.read_file(filepath)
        md_string = df.to_markdown(index=False)

        return MarkdownDoc.from_string(md_string)

    # Both
    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a string representing a csv file to markdown.

        Args:
            string (str): the string.

        Returns:
            MarkdownDoc: the markdown-formatted csv.
        """
        # Actually pd.read_csv() handles filepath as well as string and byte string.
        # We keep parse_string() to please the AbstractParser()
        return self.parse_file(string)

    def read_file(self, filepath: str) -> pd.DataFrame:
        """Read the provided filepath. For a list of handled filetypes,
        refer to https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html.

        Args:
            filepath (str): path to the file.

        Returns:
            pd.DataFrame: a dataframe.
        """
        if not filepath.lower().endswith(".csv"):
            raise ValueError("Only .csv files can be passed to CSVParser.")
        delimiter = self.csv_delimiter or CSVParser._detect_csv_delimiter(filepath)
        df = pd.read_csv(filepath, delimiter=delimiter)  # type: ignore | missing typing in pandas

        return df

    @staticmethod
    def _detect_csv_delimiter(filepath: str, n_sample_lines: int = 5) -> str:
        """Detect the delimiter used in a CSV file.

        Args:
            filepath (str): the path to a csv file.
            n_sample_lines (int): the amount of lines to consider for guessing the separator.
                Higher number may increase inference time.

        Returns:
            str : the delimiter
        """
        with open(filepath, "r", encoding="utf8") as file:
            sample = "".join([file.readline() for _ in range(n_sample_lines)])
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error as e:
            raise ValueError(
                "Could not detect the delimiter. You may want to set delimiter manually using SheetParser(csv_delimiter='<mydelimiter>') before parsing the file."
            ) from e
