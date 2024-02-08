import pytest
import re

from src.chunkers import MarkdownChunkNorris
import tests.test_strings.markdown_inputs as md_in
import tests.test_strings.markdown_outputs as md_out

@pytest.fixture(name="mdcn", scope="session")
def mdcn() -> MarkdownChunkNorris:
    return MarkdownChunkNorris()

@pytest.fixture(scope="session")
def md_standard_in() -> str:
    return md_in.MD_STANDARD

@pytest.fixture(scope="session")
def md_with_intros_in() -> str:
    return md_in.MD_WITH_INTROS

@pytest.fixture(scope="session")
def md_skipped_header_levels_in() -> str:
    return md_in.MD_SKIPPED_HEADER_LEVELS

@pytest.fixture(scope="session")
def md_standard_setext_in() -> str:
    return md_in.MD_STANDARD_SETEXT

@pytest.fixture(scope="session")
def input_strings_to_chunk() -> list[str]:
    return [
        md_in.MD_STANDARD,
        md_in.MD_WITH_INTROS,
        md_in.MD_SKIPPED_HEADER_LEVELS
        ]

@pytest.fixture(scope="session")
def output_chunks() -> list[list[str]]:
    return [
        md_out.MD_STANDARD_CHUNKS,
        md_out.MD_WITH_INTROS_CHUNKS,
        md_out.MD_SKIPPED_HEADER_LEVELS_CHUNKS
        ]

@pytest.fixture(scope="session")
def md_with_links() -> str:
    return md_in.MD_WITH_LINKS

@pytest.fixture(scope="session")
def regex_patterns_setext() -> dict:
    return {
        "h1": re.compile(r"(.+?)\n={3,}", re.MULTILINE),
        "h2": re.compile(r"(.+?)\n-{3,}", re.MULTILINE),
        "h3": re.compile(r"^(?:- )?(#{3} .+)", re.MULTILINE),
        "h4": re.compile(r"^(?:- )?(#{4} .+)", re.MULTILINE),
        "h5": re.compile(r"^(?:- )?(#{5} .+)", re.MULTILINE),
    }

@pytest.fixture(scope="session")
def regex_patterns_atx() -> dict:
    return {
        "h1": re.compile(r"^(?:- )?(#{1} .+)", re.MULTILINE),
        "h2": re.compile(r"^(?:- )?(#{2} .+)", re.MULTILINE),
        "h3": re.compile(r"^(?:- )?(#{3} .+)", re.MULTILINE),
        "h4": re.compile(r"^(?:- )?(#{4} .+)", re.MULTILINE),
        "h5": re.compile(r"^(?:- )?(#{5} .+)", re.MULTILINE),
    }

@pytest.fixture(scope="function")
def mock_toc_tree() -> dict:
    test_dict = {
        "id": -1,
        "line_index": -1,
        "level": 0,
        "title": "header 1",
        "content": "  **Sample Text\xa0\n\n\n**  ", 
        "children": [{
            "id": 0,
            "line_index": 10,
            "level": 1,
            "title": "header2",
            "content": "  **Child Text\xa0\n\n\n**  ",
            "children": [{
                "id": 1,
                "line_index": 20,
                "level":2,
                "title": "header3",
                'content': "  **ChildChild Text\xa0\n\n\n**  ",
                'children': []
                }]}]}
    test_dict["children"][0]["parent"] = test_dict
    test_dict["children"][0]["children"][0]["parent"] = test_dict["children"][0]

    return test_dict

@pytest.fixture(scope="function")
def output__cleanup_tree_text() -> dict:
    test_dict = {
        "id": -1,
        "line_index": -1,
        "level": 0,
        "title": "header 1",
        "content": "Sample Text", 
        "children": [{
            "id": 0,
            "line_index": 10,
            "level": 1,
            "title": "header2",
            "content": "Child Text",
            "children": [{
                "id": 1,
                "line_index": 20,
                "level":2,
                "title": "header3",
                'content': "ChildChild Text",
                'children': []
                }]}]}
    test_dict["children"][0]["parent"] = test_dict
    test_dict["children"][0]["children"][0]["parent"] = test_dict["children"][0]

    return test_dict

@pytest.fixture(scope="function")
def output__remove_circular_refs() -> dict:
    return {
        "id": -1,
        "line_index": -1,
        "level": 0,
        "title": "header 1",
        "content": "  **Sample Text\xa0\n\n\n**  ", 
        "children": [{
            "id": 0,
            "line_index": 10,
            "level": 1,
            "title": "header2",
            "content": "  **Child Text\xa0\n\n\n**  ",
            "children": [{
                "id": 1,
                "line_index": 20,
                "level":2,
                "title": "header3",
                'content': "  **ChildChild Text\xa0\n\n\n**  ",
                'children': []
                }]}]}


@pytest.fixture(scope="session")
def output_change_links_format() -> dict[str, str]:
    return md_out.MD_WITH_LINKS_OUTPUTS