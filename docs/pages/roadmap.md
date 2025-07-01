# 🗺️ Roadmap

Here are the ongoing developments for ``chunknorris``, or features that have been identified for future development.

Each feature is developed with **``chunknorris``' main motivation in mind: finding fast methods that require minimal computing resources**. 🌱 (Sorry dear machine learning...)

| Feature | Status |
|---------|--------|
| [PDF] Parsing of tables delimited by lines in .pdf documents | 🟢 |
| [DOCX] Parsing of .docx documents to markdown | 🟡 |
| [PDF] Title tree detection when no table of contents is present in the document | 🟡 |
| [PDF] Fix typos induced by tesseract (c.f. note 1) | 🟡 |

🔵 = ongoing
🟡 = in focus
🟢 = recently done

**Note 1 :** When using OCR on pdf documents, the backend used (Tesseract) may introduce typos. Some other tools, such as EasyOCR do not suffer that problem as much. But tesseract as the advantage of **not relying on pytorch and running fine on CPU**. Consequently, we plan on attempting to keep tesseract as a backend, but add some typo fixers.