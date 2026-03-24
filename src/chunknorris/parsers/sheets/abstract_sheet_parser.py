import re
from typing import Generic, TypeVar

import pandas as pd

from ...core.components import MarkdownDoc
from ..abstract_parser import AbstractParser, InputT


class AbstractSheetParser(AbstractParser[InputT], Generic[InputT]):
    """Base class for sheet-based parsers (CSV, Excel, etc.).
    Provides shared DataFrame conversion utilities.
    """

    @staticmethod
    def convert_df_to_markdown_table(df: pd.DataFrame) -> str:
        """Converts a DataFrame to a markdown-formatted table.
        Pre-process:
        - Remove \\n in text columns
        Post-process:
        - Replace runs of 3+ spaces with 2 spaces.
        - Collapse separator rows to exactly `---`.

        Args:
            df (pd.DataFrame): the dataframe to convert.

        Returns:
            str: a markdown formatted table.
        """
        df = df.copy()
        dtypes = df.apply(  # type: ignore | x: pd.Series[Any] -> pd.Series[str]
            lambda x: pd.api.types.infer_dtype(x, skipna=True)  # type: ignore
        )
        string_cols = dtypes[dtypes == "string"].index  # type: ignore
        df[string_cols] = df[string_cols].apply(lambda x: x.str.replace("\n", " "))  # type: ignore
        md_string = df.to_markdown(index=False)
        md_string = re.sub(r"\s{3,}", "  ", md_string)
        md_string = re.sub(r"-{3,}", "---", md_string)

        return md_string

    @staticmethod
    def convert_df_to_json_lines(df: pd.DataFrame) -> str:
        """Converts a DataFrame to JSON Lines format.

        Args:
            df (pd.DataFrame): the dataframe to convert.

        Returns:
            str: the JSON lines string.
        """
        return df.to_json(orient="records", force_ascii=False, lines=True)  # type: ignore | df.to_json() -> str

    @staticmethod
    def _df_to_markdown_doc(df: pd.DataFrame, output_format: str) -> MarkdownDoc:
        """Converts a DataFrame to a MarkdownDoc using the given output format.

        Args:
            df (pd.DataFrame): the dataframe to convert.
            output_format (str): either "markdown_table" or "json_lines".

        Returns:
            MarkdownDoc: the resulting document.
        """
        match output_format:
            case "markdown_table":
                md_string = AbstractSheetParser.convert_df_to_markdown_table(df)
            case "json_lines":
                md_string = AbstractSheetParser.convert_df_to_json_lines(df)
            case _:
                raise ValueError(
                    f"Invalid value for argument 'output_format': expected one of "
                    f"['markdown_table', 'json_lines']. Got '{output_format}'."
                )
        return MarkdownDoc.from_string(md_string)
