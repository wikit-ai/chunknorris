from collections import Counter
from itertools import groupby
import re

from thefuzz import fuzz  # type: ignore : no stubs

from .utils import PdfParserState
from .components import TocTitle


class PdfTocExtraction(PdfParserState):
    """Class intended to be used to extract the table of content
    of a document.
    Intended to be a component inherited by pdfParser => PdfParser(PdfTocExtraction)
    """

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

        toc = toc_from_metadata if toc_from_metadata else toc_from_document
        if toc:
            self._set_block_issectiontitle_with_toc(toc)
        else:
            self._set_block_issectiontitle_with_fontsize()

        return toc

    def get_toc_from_metadata(self) -> list[TocTitle] | None:
        """Uses pymupdf.get_toc() to try to get the table of
        content of the document from the metadatas.
        If it exists, builds the table of content from it

        Returns:
            list[TocTitle] | None: The toc titles found in metadatas
        """
        toc = self.document.get_toc() if self.document is not None else []  # type: ignore : missing typing in pymupdf | Document.get_toc() -> list[tuple[int, str, int, dict[str, Any]]]
        if not toc:
            return

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
            toc = PdfTocExtraction._infer_level_with_schema(toc)
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
        for i, line in enumerate(self.lines):
            match = re.match(toc_pattern, line.text)
            # regex may match ZIP codes or phone numbers => check page is less than 3 numbers
            if match and len(match[2]) < 4:
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

    @staticmethod
    def _infer_level_with_schema(toc_titles: list[TocTitle]) -> list[TocTitle]:
        """Tries to infer the titles levels based on the
        schema of the title sections. Like so:
        1. H1 title
        1.1 H2 title
        1.1.1 H3 title

        Args:
            toc_titles (list[TocTitle]): The list of toc title

        Returns:
            list[TocTitle]: the list of toc title with the level set (if schema found)
        """
        h1_pattern = re.compile(r"^(\d+)[\s\.\)]*")
        h2_pattern = re.compile(r"^(\d+)[\s\.\)]+(\d+)")
        h3_pattern = re.compile(r"^(\d+)[\s\.\)]+(\d+)[\s\.\)]+(\d+)")

        for t in toc_titles:
            for pattern, level in zip((h3_pattern, h2_pattern, h1_pattern), (3, 2, 1)):
                match = re.match(pattern, t.text)
                if match:
                    t.level = level
                    break

        return toc_titles

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
                ratio = fuzz.ratio(  # type: ignore : missing typing in fuzz | fuzz.ratio(s1 : str, s2: str) -> int
                    title.text.lower(), block.text.lower()
                )
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_block = block
            if best_block and best_ratio >= 75:
                title.found = True
                best_block.section_title = title

    def _set_block_issectiontitle_with_fontsize(self) -> None:
        """Uses the fontize attribute of blocks to assign
        them a header level.
        We assume that bigger fontsize means higher level header.
        All block having a fontisze greater than the fontsize of body
        will be assigned a level based on their fontsize.
        """
        fontsize_counts = Counter(
            block.fontsize for block in self.blocks if not block.is_empty
        )
        if fontsize_counts:
            main_body_fontsize = max(fontsize_counts, key=fontsize_counts.get)
            fontsizes = (
                fontsize
                for fontsize in fontsize_counts.keys()
                if fontsize > main_body_fontsize
            )
            fontsizes = sorted(fontsizes, reverse=True)[:5]
            for block in self.blocks:
                if block.fontsize in fontsizes:
                    block.section_title = TocTitle(
                        text=block.text,
                        level=fontsizes.index(block.fontsize) + 1,
                        page=block.page,
                        source="fontsize",
                    )

    def _get_document_main_title(self) -> str:
        """
        Tries to infer the main title of the document.
        It considers the blocks belong to main title if
        they are on first page and their fontsize is bigger
        that the body size of the document.

        Returns :
            (str) : the main title of the document
        """
        fontsize_counts = Counter(
            span.fontsize for span in self.spans if not span.is_empty
        )
        if fontsize_counts:
            main_body_fontsize = max(fontsize_counts, key=fontsize_counts.get)
            spans_on_first_page = [
                s for s in self.spans if s.page == 0 and not s.is_empty
            ]

            if spans_on_first_page:
                # Get the 2 biggest fontsizes of 1st page
                first_page_biggest_fontsizes = sorted(
                    Counter(
                        span.fontsize
                        for span in spans_on_first_page
                        if not span.is_empty
                    ),
                    reverse=True,
                )[:2]
                title_spans = (
                    s
                    for s in spans_on_first_page
                    if s.fontsize > main_body_fontsize * 1.1
                    and s.fontsize in first_page_biggest_fontsizes
                )
                main_title = " ".join((s.text for s in title_spans)).strip()

                return (
                    main_title[:100] + "[...]" if len(main_title) > 100 else main_title
                )

        return ""
