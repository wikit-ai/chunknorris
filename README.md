# Chunk Norris

## Goal

This project aims at improving the method of chunking documents from various sources (HTML, PDFs, ...)
An optimized chunking method might lead to smaller chunks, meaning :
- **Better relevancy of chunks** (and thus easier identification of useful chunks through embedding cosine similarity)
- **Less errors** because of chunks exceeding the API limit in terms of number of tokens
- **Less hallucinations** of generation models because of superfluous information in the prompt
- **Reduced cost** as the prompt would have reduced size

## Installation

Using Pypi, just run the following command :
```pip install chunknorris```

## Chunkers

The package features multiple ***chunkers*** that can be used independently depending on the type of document needed.

All chunkers follow a similar logic :
- Extract table of contents (= headers)
- Build chunks using the text content of a part, and put the titles of the parts it belongs to on top

![](images/chunk_method.png)

### MarkdownChunkNorris

This chunker is meant to be used **on markdown-formatted text**. 

Note: When calling the chunker, **you need to specify the header style** of your markdown text ([ATX or Setext](https://golem.ph.utexas.edu/~distler/maruku/markdown_syntax.html#header)). By default it will consider "Setext" heading style.

#### Usage

```py
from chunkers import MarkdownChunkNorris

text = """
# This is a header
This is a text
## This is another header
And another text
## With this final header
And this last text
"""
chunker = MarkdownChunkNorris()
header_style = "atx" # or "setext" depending on headers in your text
chunks = chunker(text, header_style=header_style)
```

### HTMLChunkNorris

This chunker is meant to be used **on html-formatted text**. Behind the scene, it uses markdownify to transform the text to markdown with "setex"-style headers and uses MarkdownChunkNorris to process it.

#### Usage

```py
from chunkers import HTMLChunkNorris

text = """
<h1>This is 1st level heading</h1>
<p>This is a test paragraph.</p>
<h2>This is 2nd level heading</h2>
<p>This is a test paragraph.</p>
<h2>This is another level heading</h2>
<p>This is another test paragraph.</p>
"""
hcn = HTMLChunkNorris()
chunks = hcn(text)
```

### Advanced usage of chunkers

Additionally, the chunkers can take a number of argument allowing to modifiy its behavior:

```py
from chunkers import MarkdownChunkNorris

mystring = "# header\nThis is a markdown string"

chunker = MarkdownChunkNorris() # or any other chunker
chunks = chunker(
    mystring,
    max_title_level_to_use="h3",
    max_chunk_word_length=200,
    link_placement="in_sentence",
    max_chunk_tokens=8191,
    chunk_tokens_exceeded_handling="split",
    min_chunk_wordcount=15,
    )
```

***max_title_level_to_use*** 
(str): The maximum (included) level of headers take into account for chunking. For example, if "h3" is set, then "h4" and "h5" titles won't be used. Must be a string of type "hx" with x being the title level. Defaults to "h4".

***max_chunk_word_length***
(int): The maximum size (soft limit, in words) a chunk can be. Chunk bigger that this size will be chunked using lower level headers, until no lower level headers are available. Defaults to 200.

***link_placement***
(str): How the links should be handled. Defaults to in_sentence.
Options :
- "remove" : text is kept but links are removed
- "end_of_chunk" : adds a paragraph at the end of the chunk containing all the links
- "in_sentence" : the links is added between parenthesis inside the sentence

***max_chunk_tokens***
(int): The hard maximum of number of token a chunk can be. Chunks bigger by this limit will be handler according to chunk_tokens_exceeded_handling. Defaults to 8191. 

***chunk_tokens_exceeded_handling***
(str): how the chunks bigger that than specified by max_chunk_tokens should be handled. Default to "raise_error".
Options: 
- "raise_error": raises an error, indicated the chunk could not be split according to headers
- "split": split the chunks arbitrarily sothat each chunk has a size lower than max_chunk_tokens

***min_chunk_wordcount***
(int): Minimum number of words to consider keeping the chunks. Chunks with less words will be discarded. Defaults to 15.

### PDFChunkNorris

#TODO: