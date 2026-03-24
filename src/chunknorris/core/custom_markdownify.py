import copy
from io import StringIO
from typing import Any

import pandas as pd
from bs4.element import Tag
from markdownify import MarkdownConverter  # type: ignore : no stubs

from .logger import LOGGER

_STRUCTURAL_ATTRS = {"rowspan", "colspan"}


def _has_merged_cells(el: Tag) -> bool:
    """Returns True if any cell in the table has a rowspan or colspan > 1."""
    return any(
        int(cell.get("rowspan", 1)) > 1 or int(cell.get("colspan", 1)) > 1
        for cell in el.find_all(["td", "th"])
    )


def _strip_attrs(el: Tag) -> Tag:
    """Returns a deep copy of the table element with all HTML attributes removed
    except rowspan and colspan, which are needed to preserve the table structure."""
    el_copy = copy.deepcopy(el)
    for tag in el_copy.find_all(True):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in _STRUCTURAL_ATTRS}
    return el_copy


class CustomMarkdownConverter(MarkdownConverter):
    """A custom MarkdownConverter that handles HTML tables.

    - Tables with merged cells (rowspan/colspan) are kept as raw HTML,
      since flattening merged cells can spread long cell values across many columns.
      Non-structural attributes (class, style, …) are stripped for token efficiency.
    - Tables without merged cells are converted to pipe-table Markdown via pandas,
      which is more token-efficient.

    In both cases, convert_table uses str(el) to access the original BS4 element
    directly — markdownify never mutates elements in place, so no No-Op overrides
    on td/tr/th are needed.
    """

    def convert_table(self, el: Tag, _text: str, parent_tags: Any) -> str:
        if _has_merged_cells(el):
            return "\n\n" + str(_strip_attrs(el)) + "\n\n"
        try:
            df = pd.read_html(StringIO(str(el)), displayed_only=False)[0]  # type: ignore : missing typing in pandas
            df = df.fillna("")  # type: ignore : missing typing in pandas
            # if no table header -> set first row as header
            if all(df.columns == list(range(len(df.columns)))):
                df.columns = df.iloc[0]
                df = df.iloc[1:]
            return "\n\n" + df.to_markdown(index=False) + "\n\n"
        except Exception as e:
            LOGGER.warning("Error converting table: %s", e)
            return "\n\n"
