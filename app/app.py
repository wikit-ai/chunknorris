import json
import time
from pathlib import Path
from typing import Literal

import requests
import tiktoken
from chunknorris.chunkers import MarkdownChunker
from chunknorris.parsers import (
    AbstractParser,
    CSVParser,
    DocxParser,
    ExcelParser,
    HTMLParser,
    MarkdownParser,
    PdfParser,
)
from chunknorris.pipelines import PdfPipeline
import streamlit as st
from streamlit import session_state as ss
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec

st.set_page_config(
    layout="wide",
    page_icon="🔪",
    page_title="ChunkNorris demo",
    menu_items={
        "Report a bug": "https://github.com/wikit-ai/chunknorris/issues",
        "About": "https://wikit-ai.github.io/chunknorris/",
    },
)

LOGGER = st.empty()

SAMPLE_FILE = {
    "sample PDF - 264 pages": "https://raw.githubusercontent.com/wikit-ai/chunknorris/refs/heads/main/docs/examples/example_data/sample.pdf",
    "sample PDF - 16 pages": "https://raw.githubusercontent.com/wikit-ai/chunknorris/refs/heads/main/docs/examples/example_data/sample2.pdf",
    "sample MD": "https://raw.githubusercontent.com/wikit-ai/chunknorris/refs/heads/main/README.md",
    "sample XLSX": "https://raw.githubusercontent.com/wikit-ai/chunknorris/refs/heads/main/docs/examples/example_data/sample.xlsx",
}

if "parsing_time" not in ss:
    ss.parsing_time = 0

if "parsed_md" not in ss:
    ss.parsed_md = ""

if "chunks" not in ss:
    ss.chunks = []  # type: ignore | list[Chunk]


def get_parser(fileext: str) -> AbstractParser:
    """Get the pipeline for the given filename."""
    match fileext:
        case ".md":
            parser = MarkdownParser()
        case ".html":
            parser = HTMLParser()
        case ".pdf":
            parser = PdfParser(
                use_ocr="never",
            )
        case ".docx":
            parser = DocxParser()
        case ".xls" | ".xlsx" | ".xlsm" | ".xlsb" | ".odf" | ".ods" | ".odt":
            parser = ExcelParser()
        case ".csv":
            parser = CSVParser()
        case _:
            raise ValueError("File format not supported by ChunkNorris")

    return parser


def get_md_chunker() -> MarkdownChunker:
    """Considering arguments set, returns the md chunker."""
    return MarkdownChunker(
        max_headers_to_use=ss.max_headers_to_use,
        max_chunk_word_count=ss.max_chunk_word_count,
        hard_max_chunk_word_count=ss.hard_max_chunk_word_count,
        min_chunk_word_count=ss.min_chunk_word_count,
        hard_max_chunk_token_count=ss.hard_max_chunk_token_count,
        tokenizer=tiktoken.encoding_for_model("text-embedding-ada-002"),
    )


def parse_and_chunk(uploaded_file: UploadedFile | None):
    """Parse and chunk the file."""
    if uploaded_file is None:
        log("Please upload a file.", "warning")
        return
    log("Parsing and chunking...", "info")

    try:
        fileext = Path(uploaded_file.name).suffix.lower()
        parser = get_parser(fileext)
        start_time = time.perf_counter()
        match fileext:
            case ".pdf":
                md_doc = parser.parse_string(uploaded_file.getvalue())
                chunker = PdfPipeline(parser, get_md_chunker())
                chunks = chunker._get_chunks_using_strategy()  # type: ignore
            case ".xlsx":
                md_doc = parser.parse_string(uploaded_file.getvalue())
                chunker = get_md_chunker()
                chunks = chunker.chunk(md_doc)
            case _:
                md_doc = parser.parse_string(uploaded_file.getvalue().decode("utf-8"))
                chunker = get_md_chunker()
                chunks = chunker.chunk(md_doc)

        ss.parsing_time = time.perf_counter() - start_time
        ss.parsed_md = md_doc.to_string()
        ss.chunks = chunks
        log(
            f"Parsing and chunking took {round(ss.parsing_time, 4)} seconds.", "success"
        )

    except Exception as e:
        log(f"Error when parsing file.", "warning")
        print(e)
        return


def save_parsed_md():
    """Save the parsed markdown string to a md file."""
    return ss.parsed_md.encode("utf-8")


def save_chunks():
    """Save the parsed chunks to a json file."""
    return json.dumps(
        [
            {
                k: v
                for k, v in chunk.model_dump().items()
                if k not in ["headers", "content"]
            }
            | {"text": chunk.get_text(prepend_headers=ss.prepend_headers_to_chunks)}
            for chunk in ss.chunks
        ],
        indent=4,
        ensure_ascii=False,
    ).encode("utf-8")


def log(message: str, log_type: Literal["success", "warning", "info"] = "info"):
    """Display a warning message."""
    match log_type:
        case "warning":
            LOGGER.warning(message, icon="⚠️")
        case "success":
            LOGGER.success(message, icon="✅")
        case "info":
            LOGGER.info(message, icon="ℹ️")


def load_sample_file(url: str):
    """Get the file from url"""
    response = requests.get(url)
    if response.status_code == 200:
        return UploadedFile(
            record=UploadedFileRec(
                file_id="sample_file",
                name=url.split("/")[-1],
                data=response.content,
                type="application/octet-stream",
            ),
            file_urls=[url],
        )
    else:
        print(response.status_code, response.content)
        st.error("Failed to get data.")
        return None


st.title("ChunkNorris.")
st.subheader("*Fast, smart, lightweight document chunking.*")

st.sidebar.header("Chunking settings")
st.sidebar.markdown(
    "| [Documentation](https://wikit-ai.github.io/chunknorris/) | [Tutorials](https://wikit-ai.github.io/chunknorris/examples/) | [Repo](https://github.com/wikit-ai/chunknorris) |"
)
st.sidebar.select_slider(
    label="Max header level to consider for chunking",
    options=["h1", "h2", "h3", "h4", "h5", "h6"],
    value="h4",
    key="max_headers_to_use",
    help="Max section header level to consider for chunking. Lower level headers won't be used to split a chunk into smaller chunks.",
    label_visibility="visible",
)

st.sidebar.slider(
    label="Maximum words (soft maximum) per chunk",
    value=250,
    min_value=0,
    max_value=3000,
    step=50,
    key="max_chunk_word_count",
    help="Maximum number of words per chunk. If a chunk is bigger than this, chunk is split using subsection headers if any are available.",
    label_visibility="visible",
)

st.sidebar.slider(
    label="Maximum words (hard maximum) per chunk",
    value=400,
    min_value=100,
    max_value=3000,
    step=50,
    key="hard_max_chunk_word_count",
    help="The hard maximum number of words per chunk. If a chunk is bigger than this, chunk is split using newlines, still trying to preverse code blocks or tables integrity.",
    label_visibility="visible",
)

st.sidebar.slider(
    label="Maximum token (hard maximum) per chunk",
    value=400,
    min_value=100,
    max_value=8000,
    step=100,
    key="hard_max_chunk_token_count",
    help="The hard maximum number of tokens per chunk. If a chunk is bigger than this, chunk is split using newlines. Applied after the word-based chunking",
    label_visibility="visible",
)

st.sidebar.slider(
    label="Minumum words per chunk",
    value=10,
    min_value=0,
    max_value=50,
    step=1,
    key="min_chunk_word_count",
    help="The minimum words a chunk must have to avoid being discarded.",
    label_visibility="visible",
)

st.sidebar.checkbox(
    "Prepend headers to chunk's text",
    value=True,
    key="prepend_headers_to_chunks",
    label_visibility="visible",
    help="Whether or not all the parent headers should be prepended to the chunk's text content. Might improve retrieval performance of the chunk as it preserves context.",
)

_, col1, col2, _ = st.columns([0.1, 0.5, 0.3, 0.1])
with col1:
    uploaded_file = st.file_uploader(
        "Upload your own file...",
        type=[
            "md",
            "html",
            "pdf",
            "docx",
            "xls",
            "xlsx",
            "xlsm",
            "xlsb",
            "odf",
            "ods",
            "odt",
            "csv",
        ],
    )

with col2:
    sample_file = st.selectbox(
        "... Or choose a sample file from the list.",
        options=list(SAMPLE_FILE.keys()),
        index=None,
    )
    if sample_file is not None:
        st.markdown(f"[View file]({SAMPLE_FILE[sample_file]})")
        uploaded_file = load_sample_file(SAMPLE_FILE[sample_file])


if uploaded_file is not None:
    parse_and_chunk(uploaded_file)
    st.sidebar.button(
        "Parse & Chunk",
        on_click=parse_and_chunk,
        args=(uploaded_file,),
        type="primary",
        use_container_width=True,
    )
else:
    st.sidebar.button(
        "Parse & Chunk",
        on_click=log,
        args=(
            "You must upload a file first.",
            "warning",
        ),
        type="secondary",
        use_container_width=True,
    )
    ss.parsed_md = ""
    ss.chunks = []


col1, col2 = st.columns(2)
with col1:
    if uploaded_file and ss.parsed_md:
        file_parsed_md = save_parsed_md()
        cola, colb = st.columns([0.25, 0.75])
        with colb:
            st.subheader("⚙️ Parsed Document", divider="blue")
        with cola:
            st.markdown("\n")
            st.download_button(
                label="⬇️ Download",
                data=file_parsed_md,
                file_name="chunknorris_parsed_document.md",
                mime="text/markdown",
                use_container_width=True,
            )
        if Path(uploaded_file.name).suffix.lower() == ".pdf":
            st.info(
                "For the purpose of this demo, OCR on pdf documents is deactivated.",
                icon="ℹ️",
            )
        with st.expander("Parsed document", expanded=True):
            with st.container(height=600, border=False):
                st.markdown(ss.parsed_md)

with col2:
    if uploaded_file and ss.chunks:  # type: ignore | list[Chunk]
        file_chunks = save_chunks()
        cola, colb = st.columns([0.25, 0.75])
        with colb:
            st.subheader("📦 Chunks", divider="blue")
        with cola:
            st.markdown("\n")
            st.download_button(
                label="⬇️ Download",
                data=file_chunks,
                file_name="chunknorris_chunks.json",
                mime="application/json",
                use_container_width=True,
            )
        with st.container(border=False):
            for i, chunk in enumerate(ss.chunks):  # type: ignore | list[Chunk]
                with st.expander(f"Chunk {i+1}", expanded=False):
                    with st.container(height=300, border=False):
                        st.markdown(
                            chunk.get_text(prepend_headers=ss.prepend_headers_to_chunks)  # type: ignore | Chunk.get_text()
                        )
