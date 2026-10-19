import codecs

import pytest

from chunknorris.core.encoding import decode_bytes

TEXT = "Ajouté à la liste — 20 €"


@pytest.mark.parametrize(
    "data",
    [
        TEXT.encode("utf-8"),
        TEXT.encode("utf-8-sig"),
        TEXT.encode("utf-16"),
        codecs.BOM_UTF16_BE + TEXT.encode("utf-16-be"),
        TEXT.encode("utf-32"),
        TEXT.encode("cp1252"),
    ],
    ids=[
        "utf-8",
        "utf-8-bom",
        "utf-16-le-bom",
        "utf-16-be-bom",
        "utf-32-bom",
        "cp1252",
    ],
)
def test_decode_bytes(data: bytes):
    assert decode_bytes(data) == TEXT


def test_decode_bytes_empty():
    assert decode_bytes(b"") == ""


def test_decode_bytes_normalizes_newlines():
    assert decode_bytes(b"a\r\nb\rc\n") == "a\nb\nc\n"


def test_decode_bytes_last_resort_never_fails():
    # 0x81 is undefined in cp1252, and invalid in utf-8
    assert decode_bytes("é\x81".encode("latin-1")) == "é\x81"


@pytest.mark.parametrize(
    "declaration",
    [
        '<meta charset="iso-8859-2">',
        "<meta charset=ISO-8859-2>",
        '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-2">',
        '<?xml version="1.0" encoding="iso-8859-2"?>',
    ],
)
def test_decode_bytes_declared_charset(declaration: str):
    html = f"<html><head>{declaration}</head><body>Łódź</body></html>"
    assert decode_bytes(html.encode("iso-8859-2"), is_html=True) == html


def test_decode_bytes_declared_charset_ignored_if_not_html():
    html = '<meta charset="iso-8859-2">Łódź'
    assert decode_bytes(html.encode("iso-8859-2")) != html


def test_decode_bytes_declared_latin1_decoded_as_cp1252():
    html = '<meta charset="iso-8859-1">20 €'
    assert decode_bytes(html.encode("cp1252"), is_html=True) == html


def test_decode_bytes_valid_utf8_wins_over_wrong_declaration():
    html = '<meta charset="iso-8859-1">Ajouté'
    assert decode_bytes(html.encode("utf-8"), is_html=True) == html


@pytest.mark.parametrize("label", ["utf-16", "not-an-encoding"])
def test_decode_bytes_unusable_declaration_falls_back(label: str):
    html = f'<meta charset="{label}">Ajouté'
    assert decode_bytes(html.encode("cp1252"), is_html=True) == html


def test_decode_bytes_non_text_codec_declaration_falls_back():
    html = '<meta charset="base64">Ajouté'
    assert decode_bytes(html.encode("cp1252"), is_html=True) == html


def test_decode_bytes_mostly_utf8_with_stray_byte():
    data = TEXT.encode("utf-8") + b" caf\xe9"
    assert decode_bytes(data) == TEXT + " caf\ufffd"


def test_decode_bytes_utf8_truncated_mid_character():
    data = TEXT.encode("utf-8")[:-2]
    assert decode_bytes(data) == TEXT[:-1] + "\ufffd"


def test_decode_bytes_mostly_cp1252_with_valid_utf8_sequence():
    # Starts with a valid UTF-8 sequence ("é"), but most of it is cp1252.
    data = "é".encode("utf-8") + TEXT.encode("cp1252")
    assert decode_bytes(data) == "Ã©" + TEXT


def test_decode_bytes_mostly_utf8_wins_over_declaration():
    html = '<meta charset="iso-8859-2">' + TEXT
    data = html.encode("utf-8") + b"\xe9"
    assert decode_bytes(data, is_html=True) == html + "\ufffd"
