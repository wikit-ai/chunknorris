from dataclasses import dataclass

import pandas as pd

# Thresholds above which a sheet is considered CSV-like.
_MIN_DATA_DENSITY = 0.6
_MIN_HEADER_QUALITY = 0.8
_MIN_ROW_CONSISTENCY = 0.7


@dataclass(frozen=True)
class SheetProfile:
    """Structural description of a sheet, used to tell CSV-like sheets
    (a header row followed by homogeneous records) from dashboard-like ones
    (titles, merged cells, sparse and irregular layout).

    The metrics are computed on a sample of the first rows, so that a profile
    can be obtained without loading very long sheets.

    Attributes:
        name (str): the name of the sheet.
        n_rows (int | None): number of data rows (header excluded), read from
            the file metadata. May include trailing empty rows that are formatted.
            None if the format does not store it (.xls, .ods...) or if it is inconsistent.
        n_columns (int): number of non-empty columns.
        data_density (float): share of non-empty cells, in [0, 1].
        header_quality (float): share of columns with a proper name, in [0, 1].
        row_consistency (float): 1 - coefficient of variation of the number
            of non-empty cells per row. 1 means all rows are equally filled.
    """

    name: str
    n_rows: int | None
    n_columns: int
    data_density: float
    header_quality: float
    row_consistency: float

    @property
    def is_csv_like(self) -> bool:
        """Whether the sheet is a CSV-like table, i.e. a header row
        followed by homogeneous records."""
        return (
            self.data_density >= _MIN_DATA_DENSITY
            and self.header_quality >= _MIN_HEADER_QUALITY
            and self.row_consistency >= _MIN_ROW_CONSISTENCY
        )

    @classmethod
    def from_dataframe(
        cls, name: str, df: pd.DataFrame, n_rows: int | None = None
    ) -> "SheetProfile":
        """Computes the profile of a sheet.

        Args:
            name (str): the name of the sheet.
            df (pd.DataFrame): the sheet, or a sample of its first rows,
                as returned by pd.read_excel().
            n_rows (int | None, optional): the number of data rows of the
                whole sheet, if known. Defaults to None.

        Returns:
            SheetProfile: the profile of the sheet.
        """
        # Empty rows and columns are usually formatting leftovers
        # that extend the used range: they say nothing about the layout.
        df = df.dropna(how="all").dropna(axis=1, how="all")
        if len(df) < 2:
            return cls(name, n_rows, len(df.columns), 0.0, 0.0, 0.0)

        data_density = float(df.count().sum() / df.size)

        valid_headers = sum(
            1
            for col in df.columns
            if pd.notna(col)
            and str(col).strip()
            and not str(col).startswith("Unnamed:")
        )
        header_quality = valid_headers / len(df.columns)

        row_counts = df.count(axis=1)
        row_consistency = float(max(0.0, 1 - row_counts.std() / row_counts.mean()))

        return cls(
            name=name,
            n_rows=n_rows,
            n_columns=len(df.columns),
            data_density=data_density,
            header_quality=header_quality,
            row_consistency=row_consistency,
        )
