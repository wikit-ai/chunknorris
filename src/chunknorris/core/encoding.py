"""Decoding of text files whose encoding is not known in advance.

Decoding order:
    1. Byte Order Mark (UTF-8, UTF-16, UTF-32).
    2. Strict UTF-8. Non-ASCII text in another encoding is almost never
       valid UTF-8, so a successful decode is reliable, even when the
       document declares another charset (a common authoring mistake).
    3. (HTML only) the charset declared in <meta> or in the XML prolog.
    4. Windows-1252, the most common legacy encoding for Western European
       languages (superset of ISO-8859-1 for printable characters).
    5. ISO-8859-1, which maps every byte, so decoding never fails.

Only strict decodes are attempted, so the cost is one pass over the data
for UTF-8 files (same as open().read()) and at most four passes otherwise. No statistical charset
detection is used: it is slow on large files and unreliable on short ones.
"""

import codecs
import io
import re
from pathlib import Path

from .logger import LOGGER

# UTF-32 BOMs must be checked before UTF-16 ones as they share a prefix.
_BOMS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)

# Only the beginning of the document is scanned for a charset declaration.
# The HTML spec uses 1024 bytes; we allow more for verbose <head> sections.
_DECLARATION_SCAN_SIZE = 4096
_RE_DECLARED_CHARSET = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-z0-9_.:-]+)"""
    rb"""|<\?xml[^>]+encoding\s*=\s*["']([a-z0-9_.:-]+)""",
    re.IGNORECASE,
)
# As browsers do (WHATWG Encoding Standard), these labels are decoded
# as Windows-1252, which they are in practice.
_WINDOWS_1252_ALIASES = {"iso8859-1", "ascii", "cp1252"}


def read_text_file(filepath: str | Path, is_html: bool = False) -> str:
    """Reads a text file whose encoding is unknown.

    Args:
        filepath (str | Path): path to the file.
        is_html (bool, optional): whether to look for a charset declaration
            in the document. Defaults to False.

    Returns:
        str: the decoded content, with newlines normalized to "\\n".
    """
    return decode_bytes(Path(filepath).read_bytes(), is_html=is_html)


def decode_bytes(data: bytes, is_html: bool = False) -> str:
    """Decodes bytes whose encoding is unknown. Never raises.

    Args:
        data (bytes): the raw content.
        is_html (bool, optional): whether to look for a charset declaration
            in the document. Defaults to False.

    Returns:
        str: the decoded content, with newlines normalized to "\\n".
    """
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            return _decode(data, encoding, errors="replace")

    try:
        return _decode(data, "utf-8")
    except UnicodeDecodeError:
        pass

    if is_html:
        declared_encoding = _find_declared_encoding(data)
        if declared_encoding is not None:
            try:
                text = _decode(data, declared_encoding)
                LOGGER.debug("Decoded document using declared %s.", declared_encoding)
                return text
            except (UnicodeDecodeError, LookupError):
                pass

    try:
        text = _decode(data, "cp1252")
        LOGGER.info("Document is not valid UTF-8. Decoded it as Windows-1252.")
        return text
    except UnicodeDecodeError:
        LOGGER.warning(
            "Could not detect document encoding. Decoded it as ISO-8859-1, "
            "some characters may be wrong."
        )
        return _decode(data, "latin-1")


def _decode(data: bytes, encoding: str, errors: str = "strict") -> str:
    # TextIOWrapper normalizes newlines while decoding, in C: about 3x faster
    # than bytes.decode() followed by str.replace().
    with io.TextIOWrapper(io.BytesIO(data), encoding=encoding, errors=errors) as f:
        return f.read()


def _find_declared_encoding(data: bytes) -> str | None:
    match = _RE_DECLARED_CHARSET.search(data[:_DECLARATION_SCAN_SIZE])
    if match is None:
        return None
    label = (match.group(1) or match.group(2)).decode("ascii")
    try:
        encoding = codecs.lookup(label).name
    except LookupError:
        return None
    if encoding in _WINDOWS_1252_ALIASES:
        return "cp1252"
    # A UTF-16/32 declaration without BOM is unreliable (WHATWG ignores it).
    if encoding.startswith(("utf-16", "utf-32")):
        return None
    return encoding
