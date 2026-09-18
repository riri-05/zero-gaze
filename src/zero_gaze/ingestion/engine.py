"""Paper ingestion engine coordinating metadata, PDF, and fallback pipelines."""

from __future__ import annotations

import logging
from zero_gaze.core.errors import IngestionError
from zero_gaze.core.models.paper import PaperArtifact, PaperExtractionSource
from zero_gaze.ingestion.arxiv_client import ArxivClient
from zero_gaze.ingestion.markdown_parser import MarkdownParser

logger = logging.getLogger(__name__)


class PaperIngestionEngine:
    """Orchestrates paper ingestion across arXiv API, PDF parsing, and HTML fallbacks."""

    def __init__(
        self,
        client: ArxivClient | None = None,
        parser: type[MarkdownParser] = MarkdownParser,
    ) -> None:
        self.client = client or ArxivClient()
        self.parser = parser

    def ingest(self, target: str) -> PaperArtifact:
        """Ingest paper by arXiv ID or URL, returning a normalized PaperArtifact."""
        arxiv_id = self.client.extract_arxiv_id(target)
        metadata = self.client.fetch_metadata(arxiv_id)

        title = metadata["title"]
        authors = metadata["authors"]
        published_date = metadata["published_date"]
        abstract = metadata["abstract"]
        pdf_url = metadata["pdf_url"]

        # Tier 1: Primary PDF Download and PyMuPDF4LLM parsing
        try:
            logger.info("Ingestion Tier 1: Downloading PDF for %s from %s", arxiv_id, pdf_url)
            pdf_bytes = self.client.download_pdf(pdf_url)
            markdown_text, headers, tables = self.parser.parse_pdf(pdf_bytes)

            if len(markdown_text.strip()) > 100:
                logger.info("Ingestion Tier 1 succeeded for %s (%d chars)", arxiv_id, len(markdown_text))
                return PaperArtifact(
                    paper_id=arxiv_id,
                    title=title,
                    authors=authors,
                    published_date=published_date,
                    abstract=abstract,
                    pdf_url=pdf_url,
                    full_text_markdown=markdown_text,
                    extraction_source=PaperExtractionSource.PYMUPDF_MARKDOWN,
                    section_headers=headers,
                    tables=tables,
                )
            logger.warning("PDF parsing yielded empty text for %s. Attempting fallback.", arxiv_id)
        except Exception as err:
            logger.warning("Ingestion Tier 1 failed for %s: %s. Attempting fallback.", arxiv_id, err)

        # Tier 2: ar5iv HTML fallback
        try:
            logger.info("Ingestion Tier 2: Fetching ar5iv HTML for %s", arxiv_id)
            html_text = self.client.fetch_ar5iv_html(arxiv_id)
            if html_text:
                markdown_text = self.parser.parse_html_to_markdown(html_text)
                if len(markdown_text.strip()) > 100:
                    headers = self.parser.extract_headers(markdown_text)
                    tables = self.parser.extract_tables(markdown_text)
                    logger.info("Ingestion Tier 2 succeeded for %s", arxiv_id)
                    return PaperArtifact(
                        paper_id=arxiv_id,
                        title=title,
                        authors=authors,
                        published_date=published_date,
                        abstract=abstract,
                        pdf_url=pdf_url,
                        full_text_markdown=markdown_text,
                        extraction_source=PaperExtractionSource.ARXIV_HTML,
                        section_headers=headers,
                        tables=tables,
                    )
        except Exception as err:
            logger.warning("Ingestion Tier 2 failed for %s: %s. Falling back to metadata.", arxiv_id, err)

        # Tier 3: Metadata-only fallback
        logger.warning("Ingestion Tier 3: Using metadata-only fallback for %s", arxiv_id)
        fallback_markdown = f"# {title}\n\n## Abstract\n\n{abstract}"
        return PaperArtifact(
            paper_id=arxiv_id,
            title=title,
            authors=authors,
            published_date=published_date,
            abstract=abstract,
            pdf_url=pdf_url,
            full_text_markdown=fallback_markdown,
            extraction_source=PaperExtractionSource.METADATA_FALLBACK,
            section_headers=["Abstract"],
            tables=[],
        )
