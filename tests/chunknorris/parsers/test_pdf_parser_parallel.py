"""Tests for parallel table extraction in PdfParser."""

import pytest
from chunknorris.parsers import PdfParser


def test_parallel_table_extraction_produces_same_results(pdf_tables_filepath: str):
    """Test that parallel table extraction produces the same results as sequential."""
    # Sequential processing (default)
    parser_seq = PdfParser(extract_tables=True)
    doc_seq = parser_seq.parse_file(pdf_tables_filepath)
    tables_seq = parser_seq.tables

    # Parallel processing with 2 workers
    parser_parallel = PdfParser(extract_tables=True, table_extraction_max_workers=2)
    doc_parallel = parser_parallel.parse_file(pdf_tables_filepath)
    tables_parallel = parser_parallel.tables

    # Assert same number of tables found
    assert len(tables_seq) == len(tables_parallel)

    # Assert tables are on the same pages
    assert [t.page for t in tables_seq] == [t.page for t in tables_parallel]

    # Assert tables have same number of cells
    for table_seq, table_parallel in zip(tables_seq, tables_parallel):
        assert len(table_seq.cells) == len(table_parallel.cells)


def test_parallel_table_extraction_with_max_workers_1(pdf_tables_filepath: str):
    """Test that max_workers=1 falls back to sequential processing."""
    parser = PdfParser(extract_tables=True, table_extraction_max_workers=1)
    doc = parser.parse_file(pdf_tables_filepath)

    # Should still find tables
    assert len(parser.tables) == 1
    assert len(parser.tables[0].cells) == 18


def test_parallel_table_extraction_disabled_when_none(pdf_tables_filepath: str):
    """Test that max_workers=None uses sequential processing (default)."""
    parser = PdfParser(extract_tables=True, table_extraction_max_workers=None)
    doc = parser.parse_file(pdf_tables_filepath)

    # Should still find tables
    assert len(parser.tables) == 1
    assert len(parser.tables[0].cells) == 18


def test_parallel_table_extraction_with_parse_string(pdf_tables_filepath: str):
    """Test parallel processing works with parse_string (using bytes)."""
    import pymupdf

    # Read PDF as bytes
    byte_string = pymupdf.open(pdf_tables_filepath).tobytes()  # type: ignore

    # Test with parallel processing
    parser = PdfParser(extract_tables=True, table_extraction_max_workers=2)
    doc = parser.parse_string(byte_string)

    # Should find tables
    assert len(parser.tables) == 1
    assert len(parser.tables[0].cells) == 18


def test_parallel_table_extraction_multiple_workers(pdf_tables_filepath: str):
    """Test parallel processing with different worker counts."""
    for num_workers in [2, 3, 4]:
        parser = PdfParser(
            extract_tables=True, table_extraction_max_workers=num_workers
        )
        doc = parser.parse_file(pdf_tables_filepath)

        # Should find same tables regardless of worker count
        assert len(parser.tables) == 1
        assert len(parser.tables[0].cells) == 18
        assert parser.tables[0].to_pandas().shape == (4, 5)
