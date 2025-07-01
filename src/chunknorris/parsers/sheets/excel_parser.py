import re
from io import BytesIO
from pathlib import Path

import pandas as pd

from ...core.components import MarkdownDoc


class ExcelParser:
    """Parser for spreadsheets, such as Excel workbooks (.xslx). For a list of handled filetypes,
    refer to https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html"""

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Parses a excel-like file to markdown.

        Args:
            string (bytes): the path to the excel-like file.

        Returns:
            MarkdownDoc: the markdown formatted excel file.
        """
        sheets = ExcelParser.read_file(filepath)
        md_string = ExcelParser.convert_sheets_to_markdown(sheets)

        return MarkdownDoc.from_string(md_string)

    def parse_string(self, string: bytes) -> MarkdownDoc:
        """Parses a bytes string representing an excel file.

        Args:
            string (bytes): the excel as a byte string.

        Returns:
            MarkdownDoc: the markdown formatted excel file
        """
        sheets = pd.read_excel(BytesIO(string), sheet_name=None)  # type: ignore | missing typing in pandas.
        md_string = self.convert_sheets_to_markdown(sheets)

        return MarkdownDoc.from_string(md_string)

    @staticmethod
    def read_file(filepath: str) -> dict[str, pd.DataFrame]:
        """Read the provided filepath.

        Args:
            filepath (str): path to the file.

        Returns:
            dict[str, pd.DataFrame]: a mapping containing {sheet_name: corresponding_dataframe.}
        """
        path = Path(filepath)
        if path.suffix.lower() not in [
            ".xls",
            ".xlsx",
            ".xlsm",
            ".xlsb",
            ".odf",
            ".ods",
            ".odt",
        ]:
            raise ValueError(f"ExcelParser cannot parse {path.suffix.lower()} files.")
        sheets = pd.read_excel(filepath, sheet_name=None)  # type: ignore | missing typing in pandas.

        return sheets

    @staticmethod
    def convert_sheets_to_markdown(sheets: dict[str, pd.DataFrame]) -> str:
        """Handle the conversion of the sheets obtained from
        pandas.read_excel() method to markdown.

        Args:
            sheets (dict[str, pd.DataFrame]): the sheets returned from pd.read_excel(sheet_name=None).

        Returns:
            str: the markdown formatted string
        """
        md_string = ""

        for sheet_name, df in sheets.items():
            md_string += f"## {sheet_name}\n\n"
            md_string += ExcelParser.convert_df_to_markdown(df) + "\n\n"

        return md_string

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
