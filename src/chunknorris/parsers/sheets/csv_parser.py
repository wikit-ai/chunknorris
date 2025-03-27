import csv
import re

import pandas as pd

from ...core.components import MarkdownDoc
from ..abstract_parser import AbstractParser


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
        md_string = CSVParser.convert_df_to_markdown(df)

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

    @staticmethod
    def convert_df_to_markdown(df: pd.DataFrame) -> str:
        """Converts a DataFrame to markdown.
        Wraps tabula's method pd.DataFrame.to_markdown()
        between pre and post processing.

        Args:
            df (pd.DataFrame): the dataframe to convert.

        Returns:
            str: a markdown formatted table.
        """
        df = df.apply(lambda x: x.str.replace("\n", " "))  # type: ignore | x: pd.Series -> pd.Series
        md_string = df.to_markdown(index=False)
        md_string = re.sub(r"\s{3,}", "  ", md_string)
        md_string = re.sub(r"-{3,}", "---", md_string)

        return md_string
