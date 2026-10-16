from unicodedata import normalize

from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import CSVParser


def test_parse_file(csv_parser: CSVParser, csv_filepath: str):

    csv_parser.output_format = "json_lines"
    parser_output = csv_parser.parse_file(csv_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    assert all(line.text.startswith("{") for line in parser_output.content if line.text)

    csv_parser.output_format = "markdown_table"
    parser_output = csv_parser.parse_file(csv_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    assert all(line.text.startswith("|") for line in parser_output.content)


def test_parse_string(csv_parser: CSVParser, csv_filepath: str):
    with open(csv_filepath, "r", encoding="utf-8") as f:
        file_content = f.read()
    parser_output = csv_parser.parse_string(file_content)
    assert isinstance(parser_output, MarkdownDoc)


def test_parse_file_cp1252(tmp_path):
    filepath = tmp_path / "file.csv"
    filepath.write_bytes("nom;prénom\r\nDurand;Hélène\r\n".encode("cp1252"))
    md_string = (
        CSVParser(output_format="markdown_table").parse_file(str(filepath)).to_string()
    )
    md_string = normalize("NFC", md_string)
    assert "prénom" in md_string and "Hélène" in md_string


def test_parse_file_utf8_bom(tmp_path):
    filepath = tmp_path / "file.csv"
    filepath.write_bytes("nom,prénom\nDurand,Hélène\n".encode("utf-8-sig"))
    md_string = (
        CSVParser(output_format="json_lines").parse_file(str(filepath)).to_string()
    )
    assert '"nom"' in md_string and "﻿" not in md_string
