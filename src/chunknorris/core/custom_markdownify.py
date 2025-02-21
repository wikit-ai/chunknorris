from bs4 import NavigableString
import pandas as pd
from markdownify import MarkdownConverter  # type: ignore : no stubs
from io import StringIO


class CustomMarkdownConverter(MarkdownConverter):
    """A custom MarkdownConverter that handles rowspan (merged cells).

    This class is a subclass of the MarkdownConverter class from the markdownify library.
    It overrides the convert_table, convert_th, convert_tr, convert_td, convert_thead, and convert_tbody methods
    to provide a No-Op for the <th>, <tr>, <td>, <thead>, and <tbody> tags, respectively.
    For <table> tags, it converts the table to a DataFrame and then converts the DataFrame to Markdown.

    It requires pandas and tabula, which is probably why markdownify doesn't implement this natively.
    As we do have both in chunknorris, we can afford using them here to improve markdown conversion of table.
    """

    def convert_table(self, el: str, text: str, convert_as_inline: bool) -> str:
        try:
            df = pd.read_html(StringIO(str(el)), displayed_only=False)[0]  # type: ignore : missing typing in pandas
            df = df.fillna("")  # type: ignore : missing typing in pandas
            # if no table header -> set first row as header
            if all(df.columns == list(range(len(df.columns)))):
                df.columns = df.iloc[0]
                df = df.iloc[1:]
            return df.to_markdown(index=False) + "\n\n"
        except:
            return "\n\n"

    def convert_th(
        self, el: NavigableString, text: str, convert_as_inline: bool
    ) -> str:
        """This method is empty because we want a No-Op for the <th> tag."""
        # return the html as is
        return str(el)

    def convert_tr(
        self, el: NavigableString, text: str, convert_as_inline: bool
    ) -> str:
        """This method is empty because we want a No-Op for the <tr> tag."""
        return str(el)

    def convert_td(
        self, el: NavigableString, text: str, convert_as_inline: bool
    ) -> str:
        """This method is empty because we want a No-Op for the <td> tag."""
        return str(el)

    def convert_thead(
        self, el: NavigableString, text: str, convert_as_inline: bool
    ) -> str:
        """This method is empty because we want a No-Op for the <thead> tag."""
        return str(el)

    def convert_tbody(
        self, el: NavigableString, text: str, convert_as_inline: bool
    ) -> str:
        """This method is empty because we want a No-Op for the <tbody> tag."""
        return str(el)
