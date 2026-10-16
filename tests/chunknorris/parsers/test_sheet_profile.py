import numpy as np
import pandas as pd

from chunknorris.parsers import SheetProfile


def _records(n_rows: int = 20) -> pd.DataFrame:
    return pd.DataFrame(
        {"name": [f"n{i}" for i in range(n_rows)], "city": "Lyon", "age": range(n_rows)}
    )


def test_csv_like():
    profile = SheetProfile.from_dataframe("sheet", _records(), n_rows=20)
    assert profile.is_csv_like
    assert (profile.n_rows, profile.n_columns) == (20, 3)
    assert profile.data_density == profile.header_quality == 1.0


def test_dashboard_like():
    df = pd.DataFrame(
        [
            ["Total", np.nan, np.nan, 1234],
            [np.nan, np.nan, "Note", np.nan],
            ["Region", "Revenue", np.nan, np.nan],
            ["North", 10, np.nan, np.nan],
        ],
        columns=["Monthly report", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3"],
    )
    assert not SheetProfile.from_dataframe("sheet", df).is_csv_like


def test_empty_columns_and_rows_are_ignored():
    df = _records()
    df.insert(1, "Unnamed: 1", np.nan)
    df = pd.concat([df, pd.DataFrame(np.nan, index=range(10), columns=df.columns)])
    profile = SheetProfile.from_dataframe("sheet", df)
    assert profile.n_columns == 3
    assert profile.is_csv_like


def test_non_string_headers_are_valid():
    df = pd.DataFrame({0: range(5), 2025: range(5), "name": "a"})
    assert SheetProfile.from_dataframe("sheet", df).header_quality == 1.0


def test_too_small_sheets_are_not_csv_like():
    assert not SheetProfile.from_dataframe("sheet", pd.DataFrame()).is_csv_like
    assert not SheetProfile.from_dataframe("sheet", _records(1)).is_csv_like
