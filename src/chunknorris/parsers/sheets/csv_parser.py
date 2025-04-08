import csv
import re
from io import StringIO

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
        csv_string = self.read_file(filepath)

        return self.parse_string(csv_string)

    def parse_string(self, string: str) -> MarkdownDoc:
        """Parses a string representing a csv file to markdown.

        Args:
            string (str): the csv-formatted string.

        Returns:
            MarkdownDoc: the markdown-formatted csv.
        """
        delimiter = self.csv_delimiter or CSVParser._detect_csv_delimiter(string)
        df = pd.read_csv(StringIO(string), delimiter=delimiter)  # type: ignore | missing typing in pandas
        md_string = CSVParser.convert_df_to_markdown(df)

        return MarkdownDoc.from_string(md_string)

    def read_file(self, filepath: str) -> str:
        """Read the provided filepath. For a list of handled filetypes,
        refer to https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html.

        Args:
            filepath (str): path to the file.

        Returns:
            str: the csv file content as a string.
        """
        if not filepath.lower().endswith(".csv"):
            raise ValueError("Only .csv files can be passed to CSVParser.")
        with open(filepath, "r", encoding="utf8") as file:
            csv_string = "".join(file.readlines())

        return csv_string

    @staticmethod
    def _detect_csv_delimiter(csv_string: str, n_sample_lines: int = 5) -> str:
        """Detect the delimiter used in a CSV file.

        Args:
            csv_string (str): the csv file as a string.
            n_sample_lines (int): the amount of lines to consider for guessing the separator.
                Higher number may increase inference time.

        Returns:
            str : the delimiter
        """
        sample = "\n".join(csv_string.split("\n")[:n_sample_lines])
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
        Preprocess :
        - Remove \n in text columns
        PostProcess :
        - Replace multiple spaces with 2 spaces.

        Args:
            df (pd.DataFrame): the dataframe to convert.

        Returns:
            str: a markdown formatted table.
        """
        dtypes = df.apply(
            lambda x: pd.api.types.infer_dtype(x, skipna=True)  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
        )
        string_cols = dtypes[dtypes == "string"].index  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
        df[string_cols] = df[string_cols].apply(lambda x: x.str.replace("\n", " "))  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
        md_string = df.to_markdown(index=False)
        md_string = re.sub(r"\s{3,}", "  ", md_string)
        md_string = re.sub(r"-{3,}", "---", md_string)

        return md_string
