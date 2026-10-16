"""Extraction of the images of a markdown string, so that the parsers of markdown-based
formats (markdown, html, docx) expose them as DocImage, as the OCR engines do."""

import re

from .components import DocImage

# Extension of the image ids, by subtype of the data URI (data:image/<subtype>;base64,...)
_SUBTYPE_EXTENSIONS = {"jpg": "jpeg", "svg+xml": "svg", "x-icon": "ico"}

_RE_DATA_URI = re.compile(r"data:image/([\w.+-]+);base64,[A-Za-z0-9+/]+=*")
# Link target, either <...> or a url holding no spaces and only balanced parentheses
_TARGET = r"<[^>\n]*>|(?:[^\s()]|\([^\s()]*\))+"
_TITLE = r"""(?:\s+(?:"[^"\n]*"|'[^'\n]*'|\([^)\n]*\)))?"""
# ![alt](target "title")
_RE_INLINE_IMAGE = re.compile(rf"!\[([^\]\n]*)\]\(\s*({_TARGET})?{_TITLE}\s*\)")
# ![alt][label] or ![alt][]
_RE_REFERENCE_IMAGE = re.compile(r"!\[([^\]\n]*)\]\[([^\]\n]*)\]")
# [label]: target "title", with its line break
_RE_DEFINITION = re.compile(
    rf"^ {{0,3}}\[([^\]\n]+)\]:[ \t]*({_TARGET}){_TITLE}[ \t]*$\n?", re.MULTILINE
)
# ![alt](id) followed by its caption, as a blockquote
_RE_CAPTIONED_IMAGE = re.compile(r"!\[[^\]\n]*\]\(([^)\s]+)\)((?:\n>[^\n]*)+)")


def quote_image_target(target: str) -> str:
    """Escapes the characters of an image url that would end its markdown reference,
    so that it can be used as image id: ![alt](id)."""
    target = target.strip().removeprefix("<").removesuffix(">").strip()
    return target.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def sanitize_image_alt(alt: str) -> str:
    """Makes the alternative text of an image fit on a single line of ![alt](id)."""
    return " ".join(alt.split()).replace("[", "(").replace("]", ")")


def extract_images(md_string: str) -> tuple[str, dict[str, DocImage]]:
    """Gets the images of a markdown string, and rewrites their references as ![alt](id).

    - Images embedded as base64 data URIs get an id such as "img-0.png",
      and the data URI is stored in DocImage.base64.
    - Images pointing to an url get the url as id.
    - Reference-style images (![alt][label], with a [label]: target definition),
      such as the output of MarkdownDoc.to_string(include_images=True), are resolved.
    - A blockquote right under an image is considered as its caption.

    Images in code blocks are not extracted. Data URIs that do not belong
    to an image reference are removed, as they would flood the text.

    Args:
        md_string (str): the markdown string.

    Returns:
        str: the markdown string, with the images referenced as ![alt](id).
        dict[str, DocImage]: the images, mapped by id.
    """
    images: dict[str, DocImage] = {}
    ids_by_data_uri: dict[str, str] = {}

    def register(target: str) -> str:
        data_uri = _RE_DATA_URI.fullmatch(target.strip().strip("<>").strip())
        if data_uri is None:
            image_id = quote_image_target(target)
            if image_id:
                images.setdefault(image_id, DocImage(id=image_id))
            return image_id
        if data_uri.group(0) not in ids_by_data_uri:
            subtype = data_uri.group(1).lower()
            extension = _SUBTYPE_EXTENSIONS.get(subtype, subtype)
            image_id = f"img-{len(ids_by_data_uri)}.{extension}"
            ids_by_data_uri[data_uri.group(0)] = image_id
            images[image_id] = DocImage(id=image_id, base64=data_uri.group(0))
        return ids_by_data_uri[data_uri.group(0)]

    def to_reference(alt: str, target: str | None) -> str:
        image_id = register(target) if target else ""
        return f"![{alt}]({image_id})" if image_id else ""

    segments = _split_code_blocks(md_string)
    definitions = {
        label.strip().lower(): target
        for is_code, segment in segments
        if not is_code
        for label, target in _RE_DEFINITION.findall(segment)
    }

    def resolve_reference(match: re.Match[str]) -> str:
        alt, label = match.groups()
        target = definitions.get((label or alt).strip().lower())
        return match.group(0) if target is None else to_reference(alt, target)

    def drop_data_definition(match: re.Match[str]) -> str:
        return "" if _RE_DATA_URI.search(match.group(2)) else match.group(0)

    parts: list[str] = []
    for is_code, segment in segments:
        if not is_code:
            segment = _RE_INLINE_IMAGE.sub(
                lambda m: to_reference(m.group(1), m.group(2)), segment
            )
            segment = _RE_REFERENCE_IMAGE.sub(resolve_reference, segment)
            segment = _RE_DEFINITION.sub(drop_data_definition, segment)
            for image_id, quote in _RE_CAPTIONED_IMAGE.findall(segment):
                image = images.get(image_id)
                if image is not None and image.caption is None:
                    image.caption = (
                        "\n".join(
                            line.removeprefix(">").strip()
                            for line in quote.strip("\n").split("\n")
                        ).strip()
                        or None
                    )
        parts.append(segment)

    return _RE_DATA_URI.sub("", "".join(parts)), images


def _split_code_blocks(md_string: str) -> list[tuple[bool, str]]:
    """Splits a markdown string in segments, flagged as belonging
    to a fenced code block or not. Segments joined give back the string."""
    segments: list[tuple[bool, list[str]]] = []
    within_code_block = False
    for line in md_string.splitlines(keepends=True):
        is_fence = line.startswith("```") and "```" not in line.rstrip()[3:]
        is_code = within_code_block or is_fence
        if not segments or segments[-1][0] != is_code:
            segments.append((is_code, []))
        segments[-1][1].append(line)
        if is_fence:
            within_code_block = not within_code_block

    return [(is_code, "".join(lines)) for is_code, lines in segments]
