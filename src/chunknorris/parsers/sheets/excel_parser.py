import re
from io import BytesIO
from pathlib import Path
from typing import Literal

import pandas as pd

from ...core.components import MarkdownDoc
from ..abstract_parser import AbstractParser


class ExcelParser(AbstractParser):
    """Parser for spreadsheets, such as Excel workbooks (.xslx). For a list of handled filetypes,
    refer to https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html"""

    def __init__(
        self,
        output_format: Literal["markdown_table", "json_lines", "auto"] = "auto",
    ) -> None:
        """Initializes an Excel parser

        Args:
            output_format (Literal["markdown_table", "json_lines", "auto], optional): the output format of the parsed document.
                - markdown_table : uses tabula to build a markdown-formatted table.
                - json_lines : each row of the table will be output as a JSON line. Better for chunking as headers are preserved.
                - auto : will detect which format is the more suitable. CSV-like sheet will be converset to JSON lines.
                Defaults to "auto".
        """
        self.output_format = output_format

    def parse_file(self, filepath: str) -> MarkdownDoc:
        """Parses a excel-like file to markdown.

        Args:
            filepath (str): the path to the excel-like file.

        Returns:
            MarkdownDoc: the markdown formatted excel file.
        """
        sheets = self.read_file(filepath)
        md_string = self.convert_sheets_to_output_format(sheets)

        return MarkdownDoc.from_string(md_string)

    def parse_string(self, string: bytes) -> MarkdownDoc:
        """Parses a bytes string representing an excel file.

        Args:
            string (bytes): the excel as a byte string.

        Returns:
            MarkdownDoc: the markdown formatted excel file
        """
        sheets = pd.read_excel(BytesIO(string), sheet_name=None)  # type: ignore | missing typing in pandas.
        md_string = self.convert_sheets_to_output_format(sheets)

        return MarkdownDoc.from_string(md_string)

    def read_file(self, filepath: str) -> dict[str, pd.DataFrame]:
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

    def convert_sheets_to_output_format(self, sheets: dict[str, pd.DataFrame]) -> str:
        """Handle the conversion of the sheets obtained from
        pandas.read_excel() method to the specified output format.

        Args:
            sheets (dict[str, pd.DataFrame]): the sheets returned from pd.read_excel(sheet_name=None).

        Returns:
            str: the formatted string
        """
        output_string = ""

        for sheet_name, df in sheets.items():
            output_string += f"## {sheet_name}\n\n"

            format_to_use = self.output_format
            if self.output_format == "auto":
                format_to_use = self._determine_best_format(df)

            match format_to_use:
                case "markdown_table":
                    output_string += self.convert_df_to_markdown_table(df) + "\n\n"
                case "json_lines":
                    output_string += self.convert_df_to_json_lines(df) + "\n\n"
                case _:
                    raise ValueError(
                        f"Invalid value for argument 'output_format': expected one of ['markdown_table', 'json_lines']. Got '{format_to_use}'."
                    )

        return output_string

    @staticmethod
    def convert_df_to_markdown_table(df: pd.DataFrame) -> str:
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
        dtypes = df.apply(  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
            lambda x: pd.api.types.infer_dtype(x, skipna=True)  # type: ignore | x: pd.Series[Any/co]
        )
        string_cols = dtypes[dtypes == "string"].index  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
        df[string_cols] = df[string_cols].apply(lambda x: x.str.replace("\n", " "))  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
        md_string = df.to_markdown(index=False)
        md_string = re.sub(r"\s{3,}", "  ", md_string)
        md_string = re.sub(r"-{3,}", "---", md_string)

        return md_string

    @staticmethod
    def convert_df_to_json_lines(df: pd.DataFrame) -> str:
        """Converts a DataFrame to json lines.

        Args:
            df (pd.DataFrame): the dataframe to convert.

        Returns:
            str: the json lines.
        """
        return df.to_json(orient="records", force_ascii=False, lines=True)  # type: ignore | df.to_json() -> str

    def _determine_best_format(
        self, df: pd.DataFrame
    ) -> Literal["markdown_table", "json_lines"]:
        """Determine the best output format based on DataFrame characteristics.

        CSV-like sheets (good for json_lines):
        - Have clear column headers
        - Data is organized in rows with consistent structure
        - Most cells contain data (not sparse)

        Dashboard-like sheets (better for markdown_table):
        - Have merged cells or complex layout
        - Sparse data with many empty cells
        - Mixed content types in irregular patterns

        Args:
            df (pd.DataFrame): the dataframe to analyze.

        Returns:
            Literal["markdown_table", "json_lines"]: the recommended format
        """
        # Check if sheet looks CSV-like
        if self._is_csv_like(df):
            return "json_lines"
        else:
            return "markdown_table"

    @staticmethod
    def _is_csv_like(df: pd.DataFrame) -> bool:
        """Check if a DataFrame has CSV-like characteristics.

        A sheet is CSV-like if it has:
        - High data density (>= 60%)
        - Good header quality (>= 70%)
        - Consistent row structure (>= 70%)

        Args:
            df (pd.DataFrame): the dataframe to analyze.

        Returns:
            bool: True if the DataFrame appears to be CSV-like
        """
        if df.empty or len(df) < 2:
            return False

        # Check data density (percentage of non-null cells)
        total_cells = df.size
        non_null_cells = df.count().sum()
        data_density = non_null_cells / total_cells if total_cells > 0 else 0

        # Check column header quality (non-null, non-empty column names)
        valid_headers = sum(
            1
            for col in df.columns
            if col and str(col).strip() and not str(col).startswith("Unnamed")
        )
        header_quality = valid_headers / len(df.columns) if len(df.columns) > 0 else 0

        # Check row consistency (similar number of non-null values per row)
        row_counts = df.count(axis=1)
        if len(row_counts) > 1:
            row_consistency = (
                1 - (row_counts.std() / row_counts.mean())
                if row_counts.mean() > 0
                else 0
            )
        else:
            row_consistency = 1.0

        return data_density >= 0.6 and header_quality >= 0.8 and row_consistency >= 0.7
