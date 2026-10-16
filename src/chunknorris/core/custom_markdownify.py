import copy
import re
from io import StringIO
from typing import Any

import pandas as pd
from bs4.element import Tag  # type: ignore : no stubs
from markdownify import MarkdownConverter  # type: ignore : no stubs

from .logger import LOGGER
from .markdown_images import quote_image_target, sanitize_image_alt

_STRUCTURAL_ATTRS = {"rowspan", "colspan"}
_CONTENT_ATTRS = {"a": {"href", "title"}}
_RE_IMAGE_ONLY = re.compile(r"(?:\s*!\[[^\]\n]*\]\([^)\s]+\))+\s*")


def _has_merged_cells(el: Tag) -> bool:
    """Returns True if any cell in the table has a rowspan or colspan > 1."""
    return any(
        int(cell.get("rowspan", 1)) > 1 or int(cell.get("colspan", 1)) > 1
        for cell in el.find_all(["td", "th"])
    )


def _strip_attrs(el: Tag) -> Tag:
    """Returns a deep copy of the table element with all HTML attributes removed
    except rowspan and colspan (needed to preserve the table structure) and a few
    content-bearing attributes such as <a href> (needed to preserve link targets)."""
    el_copy = copy.deepcopy(el)
    for tag in el_copy.find_all(True):
        kept = _STRUCTURAL_ATTRS | _CONTENT_ATTRS.get(tag.name, set())
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in kept}
    return el_copy


class CustomMarkdownConverter(MarkdownConverter):
    """A custom MarkdownConverter that handles HTML tables and images.

    - Tables with merged cells (rowspan/colspan) are kept as raw HTML,
      since flattening merged cells can spread long cell values across many columns.
      Non-structural attributes (class, style, …) are stripped for token efficiency.
    - Tables without merged cells are converted to pipe-table Markdown via pandas,
      which is more token-efficient.

    In both cases, convert_table uses str(el) to access the original BS4 element
    directly — markdownify never mutates elements in place, so no No-Op overrides
    on td/tr/th are needed.

    Images are written as ![alt](src), without title, so that their src can be used
    as image id. Links wrapping only images are dropped, and the <figcaption> of
    a <figure> holding images is written as a blockquote right under them,
    which is how image captions are written in a MarkdownDoc.
    """

    def convert_img(self, el: Tag, text: str, parent_tags: Any) -> str:
        src = quote_image_target(str(el.get("src") or ""))
        alt = sanitize_image_alt(str(el.get("alt") or ""))
        if not src:
            return alt
        if (
            "_inline" in parent_tags
            and el.parent is not None
            and el.parent.name not in self.options["keep_inline_images_in"]
        ):
            return alt
        return f"![{alt}]({src})"

    def convert_a(self, el: Tag, text: str, parent_tags: Any) -> str:
        if text.strip() and _RE_IMAGE_ONLY.fullmatch(text):
            return text
        return super().convert_a(el, text, parent_tags)  # type: ignore : no stubs

    def convert_figure(self, el: Tag, text: str, parent_tags: Any) -> str:
        figcaption = el.find("figcaption")
        if figcaption is None or el.find("img") is None or "_inline" in parent_tags:
            return text
        # a detached copy has no parent figure, so convert_figcaption returns its text
        caption = " ".join(
            self.process_tag(copy.copy(figcaption), parent_tags=set(parent_tags)).split()  # type: ignore : no stubs
        )
        quote = f"\n> {caption}" if caption else ""
        return f"\n\n{text.strip()}{quote}\n\n"

    def convert_figcaption(self, el: Tag, text: str, parent_tags: Any) -> str:
        figure = el.find_parent("figure")
        if figure is not None and figure.find("img") is not None:
            return ""  # written by convert_figure, under the images
        return f"\n\n{text.strip()}\n\n"

    def convert_table(self, el: Tag, text: str, parent_tags: Any) -> str:
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
