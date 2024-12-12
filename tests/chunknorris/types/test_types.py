from chunknorris.parsers.markdown.components import MarkdownDoc


def test_markdowndoc(md_strings_in: list[str]):
    for string in md_strings_in:
        assert MarkdownDoc.from_string(string).to_string() == string
