from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import HTMLParser


def test_parse_string(
    html_parser: HTMLParser, html_string_in: str, html_string_out: str
):
    parser_output = html_parser.parse_string(html_string_in)
    assert isinstance(parser_output, MarkdownDoc)
    assert parser_output.to_string() == html_string_out


def test_parse_file(html_parser: HTMLParser, html_filepath: str):
    parser_output = html_parser.parse_file(html_filepath)
    assert isinstance(parser_output, MarkdownDoc)


def test_read_file_cp1252(html_parser: HTMLParser, tmp_path):
    filepath = tmp_path / "file.html"
    filepath.write_bytes(
        "<html><body><p>Ajouté à la liste</p></body></html>".encode("cp1252")
    )
    assert "Ajouté à la liste" in html_parser.read_file(str(filepath))


def test_read_file_declared_charset(html_parser: HTMLParser, tmp_path):
    filepath = tmp_path / "file.html"
    filepath.write_bytes(
        '<html><head><meta charset="iso-8859-2"></head><body><p>Łódź</p></body></html>'.encode(
            "iso-8859-2"
        )
    )
    assert "Łódź" in html_parser.read_file(str(filepath))


def test_apply_markdownify_collapses_source_newlines():
    html = (
        "<p>Pour chaque action, procédez de la façon suivante\n:</p>"
        "<ol><li>Cliquez sur le bouton <b>Oui</b>\npour confirmer.</li>"
        '<li><a href="param.htm">Paramétrez\nl\'action</a>.</li></ol>'
        "<p>Ligne 1<br>Ligne 2</p>"
        "<pre>code\n  indenté</pre>"
    )
    md_string = HTMLParser.apply_markdownify(html)
    assert "procédez de la façon suivante :" in md_string
    assert "Oui** pour confirmer." in md_string
    assert "[Paramétrez l'action](param.htm)" in md_string
    assert "Ligne 1\nLigne 2" in md_string
    assert "code\nindenté" in md_string
