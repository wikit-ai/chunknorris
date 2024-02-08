import pytest 

from src.chunkers import MarkdownChunkNorris
from src.exceptions import ChunkSizeExceeded

"""
Note : two dicts with circular refs can't be asserted equals:
assert dict_with_circular_refs_1 == dict_with_circular_refs_2
leads to infinite loop.
Consequently, assertions are made on stringified dicts
assert str(dict_with_circular_refs_1) == str(dict_with_circular_refs_2)
"""

KWARGS = {
    "max_chunk_word_length": 0,
    "header_style": "atx",
    "min_chunk_word_count": 0,
}

def test__call__(mdcn, input_strings_to_chunk, output_chunks):
    for input, output in list(zip(input_strings_to_chunk, output_chunks)):
        assert mdcn(input, **KWARGS) == output

def test_check_string_argument_is_valid():
    try:
        MarkdownChunkNorris._check_string_argument_is_valid("link_placement", "remove")
        MarkdownChunkNorris._check_string_argument_is_valid("header_style", "invalid_value")
    except AssertionError as e:
        assert str(e) == "Argument 'header_style' should be one of ['setext', 'atx']. Got 'invalid_value'"

def test_get_header_regex_patterns(mdcn, regex_patterns_atx, regex_patterns_setext):
    assert mdcn._get_header_regex_patterns("atx") == regex_patterns_atx
    assert mdcn._get_header_regex_patterns("setext") == regex_patterns_setext

def text__convert_setext_to_atx(mdcn, md_standard_in, md_standard_setext_in):
    assert mdcn._convert_setext_to_atx(md_standard_setext_in, md_standard_in)

def test_get_toc_tree():
    assert None == None

def test__remove_circular_refs(mock_toc_tree, output__remove_circular_refs):
    MarkdownChunkNorris._remove_circular_refs(mock_toc_tree)
    assert mock_toc_tree == output__remove_circular_refs

def test__cleanup_tree_texts(mock_toc_tree, output__cleanup_tree_text):
    MarkdownChunkNorris._cleanup_tree_texts(mock_toc_tree)
    assert str(mock_toc_tree) == str(output__cleanup_tree_text)

def test_get_title_by_id(mock_toc_tree, id=0):
    test = MarkdownChunkNorris.get_title_by_id(mock_toc_tree, id)
    assert str(test) == str(mock_toc_tree["children"][0])

def test__change_links_format(md_with_links, output_change_links_format):
    for arg in ["in_sentence", "end_of_chunk", "remove", "leave_as_markdown"]:
        assert MarkdownChunkNorris.change_links_format(md_with_links, arg) == output_change_links_format[arg]

def test_remove_small_chunks():
    chunks = ["One", "Two words", "Three words total"]
    assert len(MarkdownChunkNorris.remove_small_chunks(chunks, 2)) == 2

def test_get_token_count(mdcn):
    chunk = "This is a big chunk"
    assert mdcn.get_token_count(chunk) == 5

def test_split_big_chunks(mdcn):
    chunks = ["Small chunk", "This is a big chunk"]
    assert len(mdcn.split_big_chunks(chunks, max_chunk_tokens=3, chunk_tokens_exceeded_handling="split")) == 3
    assert len(mdcn.split_big_chunks(chunks, max_chunk_tokens=6, chunk_tokens_exceeded_handling="split")) == 2
    try:
        mdcn.split_big_chunks(chunks, max_chunk_tokens=3, chunk_tokens_exceeded_handling="raise_error")
    except ChunkSizeExceeded as e:
        assert str(e) == str(ChunkSizeExceeded((
                        "Found chunk bigger than the specified token limit 3:",
                        "You can disable this error and allow dummy splitting of this chunk by passing 'raise_error=False'",
                        "The chunk : This is a big chunk",
                    )))

