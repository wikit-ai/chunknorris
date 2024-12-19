from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentJsonChunkedSchemaType(BaseModel):
    type: Literal["Document", "DocumentChunk"] = Field(
        ...,
        alias="@type",
        title="Type of the chunk",
        description="Type of the chunk, can be Document or DocumentChunk",
    )


class DocumentChunkMetadata(BaseModel):
    """Document Chunk common metadata"""

    page_start: int | None = Field(
        alias="pageStart",
        title="Start page in a pageable Document (e.g. a PDF file)",
        default=None,
    )
    page_end: int | None = Field(
        alias="pageEnd", title="End page in a pageable Document", default=None
    )
    position: int | None = Field(title="Position of the Document Chunk", default=None)


class WikitJSONDocumentChunk(DocumentJsonChunkedSchemaType, DocumentChunkMetadata):
    """
    Chunk of the document for the chunked JSON format upload
    """

    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(title="Text of the chunk", default=None)

    title: str | None = Field(
        title="Title metadata",
        default=None,
    )


class WikitJSONDocument(DocumentJsonChunkedSchemaType):
    """
    Other fields of the document for the chunked JSON format upload
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["Document", "DocumentChunk"] = Field(
        ...,
        alias="@type",
        title="Type of the chunk",
        description="Type of the chunk, can be Document or DocumentChunk",
    )

    has_part: List[WikitJSONDocumentChunk] = Field(
        alias="hasPart", title="Chunks of the document", default=None
    )

    context: str | None = Field(..., alias="@context", title="Context of the document")

    identifier: str | None = Field(title="Identifier of the document", default=None)

    name: str | None = Field(title="Name of the document", default=None)

    title: str | None = Field(title="Title of the document", default=None)

    text: str | None = Field(title="Text of the document", default=None)

    description: str | None = Field(title="Description of the document", default=None)

    source: str | None = Field(title="Source of the document", default=None)

    language: str | None = Field(title="Language of the document", default=None)

    url: str | None = Field(title="Url of the document", default=None)

    keywords: List[str] | None = Field(title="Keywords of the document", default=None)

    comment: str | None = Field(title="Comment of the document", default=None)

    date_created: str | None = Field(
        alias="dateCreated", title="Date of creation", default=None
    )

    date_modified: str | None = Field(
        alias="dateModified", title="Date of the last modification", default=None
    )

    file_format: str | None = Field(
        alias="fileFormat", title="File format of the document", default=None
    )
