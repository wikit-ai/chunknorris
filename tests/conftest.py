import pytest

import tests.test_strings.chunkers.markdown_chunker as md_chunker_strings
import tests.test_strings.chunkers.tools.tools as chunker_tools_strings
import tests.test_strings.parsers.html_parser as html_parser_strings
import tests.test_strings.parsers.markdown_parser as md_parser_strings
import tests.test_strings.parsers.wikit_parser as wikit_parser_strings
from chunknorris.chunkers import MarkdownChunker
from chunknorris.core.components import Chunk
from chunknorris.parsers import (
    CSVParser,
    DocxParser,
    ExcelParser,
    HTMLParser,
    JupyterNotebookParser,
    MarkdownParser,
    PdfParser,
    WikitJsonParser,
)

################
#   Chunkers   #
################


@pytest.fixture(scope="session")
def md_chunker() -> MarkdownChunker:
    return MarkdownChunker(
        max_chunk_word_count=0, hard_max_chunk_word_count=10000, min_chunk_word_count=0
    )


###############
#   Parsers   #
###############


@pytest.fixture(scope="session")
def md_parser() -> MarkdownParser:
    return MarkdownParser()


@pytest.fixture(scope="session")
def html_parser() -> HTMLParser:
    return HTMLParser()


@pytest.fixture(scope="session")
def wikit_parser() -> WikitJsonParser:
    return WikitJsonParser()


@pytest.fixture(scope="session")
def pdf_parser() -> PdfParser:
    return PdfParser()


@pytest.fixture(scope="session")
def jupyter_notebook_parser() -> JupyterNotebookParser:
    return JupyterNotebookParser()


@pytest.fixture(scope="session")
def excel_parser() -> ExcelParser:
    return ExcelParser()


@pytest.fixture(scope="session")
def csv_parser() -> CSVParser:
    return CSVParser()


@pytest.fixture(scope="session")
def docx_parser() -> DocxParser:
    return DocxParser()


###############
#  filepaths  #
###############


@pytest.fixture(scope="session")
def md_filepath() -> str:
    return "./tests/test_files/file.md"


@pytest.fixture(scope="session")
def html_filepath() -> str:
    return "./tests/test_files/file.html"


@pytest.fixture(scope="session")
def wikitjson_md_filepath() -> str:
    return "./tests/test_files/file_md.json"


@pytest.fixture(scope="session")
def wikitjson_html_filepath() -> str:
    return "./tests/test_files/file_html.json"


@pytest.fixture(scope="session")
def pdf_filepath() -> str:
    return "./tests/test_files/file.pdf"


@pytest.fixture(scope="session")
def pdf_tables_filepath() -> str:
    return "./tests/test_files/tables.pdf"


@pytest.fixture(scope="session")
def jupyter_notebook_filepath() -> str:
    return "./tests/test_files/file.ipynb"


@pytest.fixture(scope="session")
def excel_filepath() -> str:
    return "./tests/test_files/file.xlsx"


@pytest.fixture(scope="session")
def csv_filepath() -> str:
    return "./tests/test_files/file.csv"


@pytest.fixture(scope="session")
def docx_filepath() -> str:
    return "./tests/test_files/file.docx"


@pytest.fixture(scope="session")
def docx_tables_filepath() -> str:
    return "./tests/test_files/tables.docx"


#############
#  Strings  #
#############

### MarkdownChunker ###


@pytest.fixture(scope="session")
def md_strings_in() -> list[str]:
    return [
        md_chunker_strings.MD_STANDARD_IN,
        md_chunker_strings.MD_WITH_INTROS_IN,
        md_chunker_strings.MD_SKIPPED_HEADER_LEVELS_IN,
    ]


@pytest.fixture(scope="session")
def md_strings_out() -> list[list[str]]:
    return [
        md_chunker_strings.MD_STANDARD_OUT,
        md_chunker_strings.MD_WITH_INTROS_OUT,
        md_chunker_strings.MD_SKIPPED_HEADER_LEVELS_OUT,
    ]


@pytest.fixture(scope="session")
def md_standard_in() -> str:
    return md_chunker_strings.MD_STANDARD_IN


@pytest.fixture(scope="session")
def md_standard_out() -> list[str]:
    return md_chunker_strings.MD_STANDARD_OUT


@pytest.fixture(scope="session")
def md_big_chunk_in() -> Chunk:
    return md_chunker_strings.MD_BIG_CHUNK_IN


@pytest.fixture(scope="session")
def md_big_chunk_out() -> list[str]:
    return md_chunker_strings.MD_BIG_CHUNK_OUT


### MarkdownParser ###


@pytest.fixture(scope="session")
def md_standard_setext_in() -> str:
    return md_parser_strings.MD_STANDARD_SETEXT_IN


@pytest.fixture(scope="session")
def md_standard_setext_out() -> str:
    return md_parser_strings.MD_STANDARD_SETEXT_OUT


@pytest.fixture(scope="session")
def md_with_code_block() -> str:
    return md_parser_strings.MD_WITH_CODE_BLOCK


@pytest.fixture(scope="session")
def md_with_metadata() -> str:
    return md_parser_strings.MD_WITH_METADATA


### Chunk ###


@pytest.fixture(scope="session")
def chunk_with_links() -> Chunk:
    return chunker_tools_strings.CHUNK_WITH_LINKS_IN


@pytest.fixture(scope="session")
def chunk_with_links_out() -> str:
    return chunker_tools_strings.CHUNK_WITH_LINKS_OUT


### HTMLParser ###


@pytest.fixture(scope="session")
def html_string_in() -> str:
    return html_parser_strings.HTML_STRING_IN


@pytest.fixture(scope="session")
def html_string_out() -> str:
    return html_parser_strings.HTML_STRING_OUT


###  WikitParser ###


@pytest.fixture(scope="session")
def json_string_in() -> str:
    return wikit_parser_strings.JSON_STRING_IN
