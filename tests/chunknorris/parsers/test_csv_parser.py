from chunknorris.parsers import CSVParser
from chunknorris.core.components import MarkdownDoc


def test_parse_file(csv_parser: CSVParser, csv_filepath: str):
    df = csv_parser.read_file(csv_filepath)
    assert len(df.index) == 5 and len(df.columns) == 6  # type: ignore | missing typing in pd.Index
    parser_output = csv_parser.parse_file(csv_filepath)
    assert isinstance(parser_output, MarkdownDoc)
