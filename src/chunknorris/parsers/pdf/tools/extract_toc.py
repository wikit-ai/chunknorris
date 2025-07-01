import re
from collections import Counter
from itertools import groupby

from thefuzz import fuzz  # type: ignore : no stubs

from .components import TocTitle
from .utils import PdfParserState


class PdfTocExtraction(PdfParserState):
    """Class intended to be used to extract the table of content
    of a document.
    Intended to be a component inherited by pdfParser => PdfParser(PdfTocExtraction)
    """

    @property
    def header_patterns(self) -> list[tuple[int, re.Pattern[str]]]:
        """A list of tuple (level, pattern) used to match the potential headers"""
        return [
            (3, re.compile(r"^(\d+)[\s\.\)]+(\d+)[\s\.\)]+(\d+)")),
            (2, re.compile(r"^(\d+)[\s\.\)]+(\d+)")),
            (1, re.compile(r"^(\d+)[\s\.\)]*")),
        ]

    def get_toc(self) -> list[TocTitle]:
        """Gets the table of content of a document.
        The process:
        - tries to find the toc in metadatas
        - if not found, tries to find a table of content in the document
        --- if found, tries to infer the level of header...
             --- ...with the x offset the headers in the toc, assuming lower level header are more to the right
             --- ...or trying to parse a schema, such as 1. 1.1, 1.1.a)
        - if not found, tries to infer header level with font size, assuming lower level have lower font size

        Returns:
            list[TocTitle]: the list of titles found
        """
        toc_from_metadata = self.get_toc_from_metadata()
        # Run anyway as table of content might also be in document
        # and we want to flag the lines that belong to it
        toc_from_document = self.get_toc_from_document()

        toc = None
        if toc_from_metadata:
            self._set_block_issectiontitle_with_toc(toc_from_metadata)
            # sometime, the toc in metadata doesn't represent the toc in document.
            # So, if less than half of toc are found in doc, find toc in doc.
            if self.headers_have_been_found(toc_from_metadata):
                toc = toc_from_metadata
        if toc is None and toc_from_document:
            self._set_block_issectiontitle_with_toc(toc_from_document)
            if self.headers_have_been_found(toc_from_document):
                toc = toc_from_document
        if toc is None:
            toc = self._set_block_issectiontitle_with_fontsize()

        return toc or []

    def get_toc_from_metadata(self) -> list[TocTitle]:
        """Uses pymupdf.get_toc() to try to get the table of
        content of the document from the metadatas.
        If it exists, builds the table of content from it

        Returns:
            list[TocTitle] | None: The toc titles found in metadatas
        """
        toc = self.document.get_toc() if self.document is not None else []  # type: ignore : missing typing in pymupdf | Document.get_toc() -> list[tuple[int, str, int, dict[str, Any]]]
        if not toc:
            return []

        return [
            TocTitle(text=item[1], level=item[0], page=item[2], source="metadata")
            for item in toc
        ]

    def get_toc_from_document(self) -> list[TocTitle]:
        """Tries to find a table of content in the document
        and parses it's titles. May return an ampty list
        if no table of content found

        Returns:
            list[TocTitle]: the titles found in the toc
        """
        toc = self._find_toc_titles()
        if toc:
            toc = self._infer_level_with_schema(toc)
            if not all(t.level for t in toc):
                toc = PdfTocExtraction._infer_level_with_offset(toc)

        return toc

    def _find_toc_titles(self) -> list[TocTitle] | None:
        """Tries to find the table of content based on regex matches.
        Handles the case where the title of the toc is on multiple lines
        Returns:
            list[TocTitle]: The potential titles of the table of content
                and their caracteristics
        """
        toc_pattern = re.compile(
            r"(.+?)(?:\s+)?[\.\_\-\s….]{5,}(?:\s+)?(?:[pP]\.\s*)?(\d+)"
        )

        toc_titles: list[TocTitle] = []
        until_last_match_counter = 0
        # browse through lines up to page 15 to get those which might be TOC
        for i, line in enumerate(filter(lambda x: x.page < 15, self.lines)):
            until_last_match_counter += 1
            if len(toc_titles) > 3 and until_last_match_counter > 10:
                break  # likely we have found a TOC and are now browsing through document
            match = re.match(toc_pattern, line.text)
            # regex may match ZIP codes or phone numbers => check page is less than 3 numbers
            if match and len(match[2]) < 4:
                until_last_match_counter = 0
                line.is_toc_element = True
                # multiline toc title
                if i > 2 and (
                    not self.lines[i - 1].is_toc_element
                    and self.lines[i - 2].is_toc_element
                ):
                    toc_text = self.lines[i - 1].text + match[1]
                    x_offset = self.lines[i - 1].origin.x  # type: ignore : missing typing in pymupdf | Point.x : float
                    self.lines[i - 1].is_toc_element = True
                # single line toc title
                else:
                    toc_text = match[1]
                    x_offset = line.origin.x  # type: ignore : missing typing in pymupdf | Point.x : float
                toc_titles.append(
                    TocTitle(
                        text=toc_text,
                        page=int(match[2]),
                        x_offset=int(x_offset),
                        source="regex",
                        source_page=line.page,
                    )
                )

        return toc_titles

    @staticmethod
    def _infer_level_with_offset(toc_titles: list[TocTitle]) -> list[TocTitle]:
        """Given on a list of toc_tiles found in the document,
        infer their level (h1, h2, ...) based on the x_offset
        of their bbox. We assume that a bigger x_offset means lower level
        (= text is more on the right of the document). Like so:
        A. H1 title
          a. H2 title
            1. H3 title

        Args:
            toc_titles (list[TocTitle]): list of toc titles returned by
                _find_toc_titles()

        Returns:
            list[TocTitle]: the toc titles, with the "level" value set
        """
        new_toc_titles: list[TocTitle] = []
        toc_elem_per_page = groupby(toc_titles, key=lambda x: x.source_page)
        for _, toc_elem_on_page in toc_elem_per_page:
            toc_elem_on_page = list(toc_elem_on_page)
            offsets: list[float] = sorted(
                list(set(t.x_offset for t in toc_elem_on_page))
            )
            for title in toc_elem_on_page:
                title.level = offsets.index(title.x_offset) + 1
                new_toc_titles.append(title)

        return new_toc_titles

    def _infer_level_with_schema(self, toc_titles: list[TocTitle]) -> list[TocTitle]:
        """Tries to infer the titles levels based on the
        schema of the title sections.

        Args:
            toc_titles (list[TocTitle]): The list of toc title

        Returns:
            list[TocTitle]: the list of toc title with the level set (if schema found)
        """
        for t in toc_titles:
            t.level = self._get_header_level_using_schema(t.text)

        return toc_titles

    def _get_header_level_using_schema(self, header_text: str) -> int | None:
        """Detects the header level according to specific schema such as :
        1. H1 title
        1.1 H2 title
        1.1.1 H3 title

        Args:
            header_text (str): the text to get the header level from

        Returns:
            int | None: the header level. Returns None if the regex didn't match any level
        """
        for level, pattern in self.header_patterns:
            if re.match(pattern, header_text):
                return level

    def _set_block_issectiontitle_with_toc(self, toc: list[TocTitle]) -> None:
        """After finding the toc, this modifies
        blocks among self.blocks attributes of the PdfParser
        to set which ones are the section's headers.
        """
        for title in toc:
            pages_to_look_on = range(title.page - 1, title.page + 2)
            blocks_to_consider = (
                block for block in self.blocks if block.page in pages_to_look_on
            )
            best_ratio, best_block = 0, None
            for block in blocks_to_consider:
                # if the first line of the block corresponds to the title text -> toc title
                if block.lines[0].text.lower() == title.text.lower():
                    block.lines[0].is_toc_element = True
                    best_ratio = 100
                    best_block = block
                    break
                # else check if title text is similar to block text
                ratio = fuzz.ratio(  # type: ignore : missing typing in fuzz | fuzz.ratio(s1 : str, s2: str) -> int
                    title.text.lower(), block.text.lower()
                )
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_block = block
            if best_block and best_ratio >= 75:
                title.found = True
                best_block.section_title = title

    def _set_block_issectiontitle_with_fontsize(self) -> list[TocTitle]:
        """Uses the fontize attribute of lines to assign
        them a header level to blocks.
        We assume that bigger fontsize means higher level header.
        All block having a fontsize greater than the fontsize of body
        will be assigned a level based on their fontsize.
        """
        toc: list[TocTitle] = []
        # Get header fontsizes
        if not self.main_body_fontsizes or not self.document_fontsizes:
            return toc
        biggest_body_fontsize = max(self.main_body_fontsizes)
        header_fontsizes = (
            fontsize
            for fontsize in self.document_fontsizes
            if fontsize > biggest_body_fontsize
        )
        header_fontsizes = sorted(header_fontsizes, reverse=True)[:5]
        for block in self.blocks:
            supposed_header_level = None
            if (
                block.orientation != (1.0, 0.0)
                or block.is_empty
                or len(block.text) > 100
            ):
                # do not consider non-horizontal text or long texts as they are unlikely to be headers
                continue
            elif block.fontsize in header_fontsizes:  # likely to be a header
                supposed_header_level = header_fontsizes.index(block.fontsize) + 1
            elif (
                block.fontsize == biggest_body_fontsize
                and block.is_bold
                and not self.main_body_is_bold
            ):  # likely to be a header
                supposed_header_level = len(header_fontsizes) + 1

            if supposed_header_level:
                header_level = (
                    self._get_header_level_using_schema(block.text)
                    or supposed_header_level
                )
                toc_title = TocTitle(
                    text=block.text,
                    level=header_level,
                    page=block.page,
                    source="fontsize",
                    found=True,
                )
                block.section_title = toc_title
                toc.append(toc_title)

        return toc

    def _get_document_main_title(self) -> str:
        """
        Tries to infer the main title of the document.
        It considers the blocks belong to main title if
        they are on first page and their fontsize is bigger
        that the body size of the document.

        Returns :
            (str) : the main title of the document
        """
        spans_on_first_page = [s for s in self.spans if s.page == 0 and not s.is_empty]
        if spans_on_first_page and self.main_body_fontsizes:
            # Get the 2 biggest fontsizes of 1st page
            first_page_biggest_fontsizes = sorted(
                Counter(
                    span.fontsize
                    for span in spans_on_first_page
                    if not span.is_empty and span.orientation == (1.0, 0.0)
                ),
                reverse=True,
            )[:2]
            title_spans = (
                s
                for s in spans_on_first_page
                if s.fontsize not in self.main_body_fontsizes
                and s.fontsize in first_page_biggest_fontsizes
            )
            main_title = " ".join((s.text for s in title_spans)).strip()

            return main_title[:100] + "[...]" if len(main_title) > 100 else main_title

        return ""

    def headers_have_been_found(self, toc: list[TocTitle]) -> bool:
        """Given a potential ToC, determines whether the headers have been
        found in the document.
        If more than half the headers have been found, returns True.
        Otherwise retruns False, indicating that detected the ToC might be wrong.

        Returns:
            bool : True if detected headers have been found in document.
        """
        if len(toc) < 3:
            return False
        headers_found = [header for header in toc if header.found]
        return len(headers_found) / len(toc) > 0.5
