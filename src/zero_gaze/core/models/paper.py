"""Paper ingestion artifact domain model."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PaperExtractionSource(str, Enum):
    """Source from which paper content was extracted."""

    PYMUPDF_MARKDOWN = "pymupdf_markdown"
    ARXIV_HTML = "arxiv_html"
    METADATA_FALLBACK = "metadata_fallback"


class PaperArtifact(BaseModel):
    """Normalized paper artifact extracted from arXiv or PDF."""

    model_config = ConfigDict(frozen=True)

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    published_date: str | None = None
    abstract: str
    pdf_url: str
    full_text_markdown: str
    extraction_source: PaperExtractionSource = PaperExtractionSource.PYMUPDF_MARKDOWN
    section_headers: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
