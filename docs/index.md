# Welcome to ChunkNorris' documentation !

![](./assets/chunknorris_logo_extended.png)

## What is ``chunknorris`` ?

In a nutshell, ``chunknorris`` is a python package that aims at drastically <span style="color:#FF6E42">**improve the chunking of documents**</span> from various sources (HTML, PDFs, Markdown, ...) while <span style="color:#FF6E42">**keeping the usage of computational ressources to the minimum**</span>.

## Why should I use it ?

In the context of Retrieval Augmented Generation (RAG), an optimized chunking strategy leads to :

- **Better relevancy of chunks** and thus easier identification of useful chunks through more expressive embeddings.
- **Less hallucinations** of generation models because of superfluous information in the prompt
- **Less errors** because of chunks exceeding the API limits in terms of number of tokens
- **Reduced cost** as the prompt can have reduced size

As of today, many packages exist with the intent of parsing documents. Though the vast majority of them :

- rely on **high computational requirements**
- **do not provide chunks out of the box**, and instead provide parsing of the documents on top of which the user has to build the chunking implementation.