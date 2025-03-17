from chunknorris.core.components import MarkdownDoc
from chunknorris.parsers import ExcelParser


def test_parse_file(excel_parser: ExcelParser, excel_filepath: str):
    sheets = excel_parser.read_file(excel_filepath)
    assert len(sheets) == 2
    df = sheets["sheet1"]
    assert len(df.index) == 5 and len(df.columns) == 6  # type: ignore | missing typing in pd.Index
    parser_output = excel_parser.parse_file(excel_filepath)
    assert isinstance(parser_output, MarkdownDoc)
