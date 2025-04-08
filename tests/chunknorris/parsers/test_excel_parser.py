from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import ExcelParser


def test_read_file(excel_parser: ExcelParser, excel_filepath: str):
    sheets = excel_parser.read_file(excel_filepath)
    assert len(sheets) == 2
    df = sheets["sheet1"]
    assert len(df.index) == 5 and len(df.columns) == 6  # type: ignore | missing typing in pd.Index


def test_parse_file(excel_parser: ExcelParser, excel_filepath: str):
    parser_output = excel_parser.parse_file(excel_filepath)
    assert isinstance(parser_output, MarkdownDoc)
    lines = parser_output.to_string().split("\n")
    assert sum(line.startswith("#") for line in lines) == 2
    assert sum(line.startswith("|") for line in lines) == 14


def test_parse_string(excel_parser: ExcelParser, excel_filepath: str):
    with open(excel_filepath, "rb") as f:
        file_content = f.read()
    parser_output = excel_parser.parse_string(file_content)
    assert isinstance(parser_output, MarkdownDoc)
    lines = parser_output.to_string().split("\n")
    assert sum(line.startswith("#") for line in lines) == 2
    assert sum(line.startswith("|") for line in lines) == 14
