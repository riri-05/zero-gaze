# Lego 01: Paper Ingestion & Markdown Engine

## 1. Overview & Responsibility
The **Paper Ingestion & Markdown Engine** transforms unstructured academic papers (arXiv links, PDF URLs, or local files) into normalized, clean Markdown preserving LaTeX mathematical formulas, tabular benchmarks, and section hierarchy.

```
[arXiv URL / ID] ──► [arXiv Query API] ──► [PDF Binary Stream] ──► [PyMuPDF4LLM] ──► [PaperArtifact (Pydantic)]
                                                                          │ (Fallback)
                                                                          ▼
                                                                [ar5iv HTML Extractor]
```

---

## 2. Official Provider Documentation Links
- **arXiv API User Manual:** [`https://info.arxiv.org/help/api/user-manual.html`](https://info.arxiv.org/help/api/user-manual.html)
- **arXiv Export Endpoint:** [`http://export.arxiv.org/api/query?id_list={arxiv_id}`](http://export.arxiv.org/api/query)
- **PyMuPDF4LLM Documentation:** [`https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/`](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
- **PyMuPDF Repository:** [`https://github.com/pymupdf/pymupdf4llm`](https://github.com/pymupdf/pymupdf4llm)
- **Ar5iv (HTML Paper Renderer):** [`https://ar5iv.labs.arxiv.org/`](https://ar5iv.labs.arxiv.org/)

---

## 3. Data Contract & Domain Model

```python
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class PaperExtractionSource(str, Enum):
    PYMUPDF_MARKDOWN = "pymupdf_markdown"
    ARXIV_HTML = "arxiv_html"
    METADATA_FALLBACK = "metadata_fallback"


class PaperArtifact(BaseModel):
    paper_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    published_date: Optional[str] = None
    abstract: str
    pdf_url: str
    full_text_markdown: str
    extraction_source: PaperExtractionSource
    section_headers: List[str] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
```

---

## 4. Implementation Pattern

```python
import re
import urllib.request
import xml.etree.ElementTree as ET
import pymupdf4llm


class ArxivPaperIngestion:

    @staticmethod
    def extract_arxiv_id(target: str) -> str:
        """Extracts canonical arXiv ID from URLs or bare IDs (e.g. 2106.09685)."""
        match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", target)
        if match:
            return match.group(1)
        raise ValueError(f"Could not parse valid arXiv ID from: {target}")

    @classmethod
    def fetch_metadata(cls, arxiv_id: str) -> dict:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "ZeroGaze/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            raise RuntimeError(f"arXiv ID {arxiv_id} not found.")

        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip()
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        return {
            "title": title,
            "abstract": summary,
            "authors": authors,
            "pdf_url": pdf_url,
        }

    @classmethod
    def extract_markdown(cls, pdf_bytes: bytes) -> str:
        """Runs pymupdf4llm over PDF bytes to extract high-fidelity markdown."""
        return pymupdf4llm.to_markdown(doc=pdf_bytes)
```

---

## 5. Failure Modes & Recovery Hierarchy
1. **Corrupted or Blocked PDF Download:**
   - Fallback to `ar5iv.labs.arxiv.org/html/{arxiv_id}` to retrieve HTML DOM.
2. **Scanned Papers (Zero Text Layer):**
   - Fallback to arXiv title and abstract metadata (`METADATA_FALLBACK`). An explicit warning flag is set in `AgentState.errors`.
3. **Rate Limits on arXiv API:**
   - Implement exponential backoff (initial delay 3s, multiplier 2x, max retries 3) with custom `User-Agent`.
