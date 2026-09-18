"""Unit tests for arXiv paper ingestion and markdown engine."""

from unittest.mock import MagicMock, patch
import pytest
from zero_gaze.core.errors import IngestionError
from zero_gaze.core.models.paper import PaperExtractionSource
from zero_gaze.ingestion.arxiv_client import ArxivClient
from zero_gaze.ingestion.engine import PaperIngestionEngine
from zero_gaze.ingestion.markdown_parser import MarkdownParser

MOCK_ATOM_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>LoRA: Low-Rank Adaptation of
    Large Language Models</title>
    <summary>An empirical study of low rank adaptation.</summary>
    <published>2021-06-17T17:37:18Z</published>
    <author><name>Edward J. Hu</name></author>
    <author><name>Yelong Shen</name></author>
  </entry>
</feed>
"""

MOCK_EMPTY_FEED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>
"""


def test_extract_arxiv_id_valid() -> None:
    cases = [
        ("2106.09685", "2106.09685"),
        ("2106.09685v2", "2106.09685v2"),
        ("arXiv:2106.09685", "2106.09685"),
        ("https://arxiv.org/abs/2106.09685", "2106.09685"),
        ("https://arxiv.org/pdf/2106.09685.pdf", "2106.09685"),
        ("https://arxiv.org/html/2106.09685v1", "2106.09685v1"),
    ]
    for raw, expected in cases:
        assert ArxivClient.extract_arxiv_id(raw) == expected


def test_extract_arxiv_id_invalid() -> None:
    with pytest.raises(IngestionError):
        ArxivClient.extract_arxiv_id("not-a-valid-paper-id")


def test_fetch_metadata_success() -> None:
    client = ArxivClient()
    with patch.object(client, "_make_request", return_value=MOCK_ATOM_XML):
        meta = client.fetch_metadata("2106.09685")
        assert meta["paper_id"] == "2106.09685"
        assert meta["title"] == "LoRA: Low-Rank Adaptation of Large Language Models"
        assert meta["authors"] == ["Edward J. Hu", "Yelong Shen"]
        assert meta["published_date"] == "2021-06-17T17:37:18Z"
        assert meta["pdf_url"] == "https://arxiv.org/pdf/2106.09685.pdf"


def test_fetch_metadata_not_found() -> None:
    client = ArxivClient()
    with patch.object(client, "_make_request", return_value=MOCK_EMPTY_FEED_XML):
        with pytest.raises(IngestionError) as exc_info:
            client.fetch_metadata("9999.99999")
        assert "No entry found" in str(exc_info.value)


def test_download_pdf_validates_header() -> None:
    client = ArxivClient()
    with patch.object(client, "_make_request", return_value=b"<html>Not a PDF</html>"):
        with pytest.raises(IngestionError) as exc_info:
            client.download_pdf("https://arxiv.org/pdf/invalid.pdf")
        assert "valid PDF header" in str(exc_info.value)


def test_markdown_parser_extract_headers() -> None:
    sample_md = """
    # Section One
    Some text here.
    ## Section Two: Details
    More content.
    ### Subsection 2.1
    Inner content.
    """
    headers = MarkdownParser.extract_headers(sample_md)
    assert headers == ["Section One", "Section Two: Details", "Subsection 2.1"]


def test_markdown_parser_extract_tables() -> None:
    sample_md = """
    # Results

    | Model | Score | Latency |
    |---|---|---|
    | LoRA | 89.5 | 12ms |
    | Baseline | 82.1 | 45ms |

    Paragraph text.
    """
    tables = MarkdownParser.extract_tables(sample_md)
    assert len(tables) == 1
    assert tables[0]["headers"] == ["Model", "Score", "Latency"]
    assert len(tables[0]["rows"]) == 2
    assert tables[0]["rows"][0]["Model"] == "LoRA"
    assert tables[0]["rows"][0]["Score"] == "89.5"


def test_markdown_parser_empty_pdf_raises() -> None:
    with pytest.raises(IngestionError):
        MarkdownParser.parse_pdf(b"")


def test_markdown_parser_html_to_markdown() -> None:
    sample_html = """
    <html>
      <body>
        <h1>Paper Title</h1>
        <p>This is a paragraph.</p>
        <ul>
          <li>Point 1</li>
          <li>Point 2</li>
        </ul>
      </body>
    </html>
    """
    md = MarkdownParser.parse_html_to_markdown(sample_html)
    assert "# Paper Title" in md
    assert "This is a paragraph." in md
    assert "- Point 1" in md


def test_engine_tier1_success() -> None:
    client = ArxivClient()
    mock_meta = {
        "title": "Mock Paper",
        "authors": ["Author A"],
        "published_date": "2024-01-01",
        "abstract": "Abstract",
        "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
    }
    with patch.object(client, "fetch_metadata", return_value=mock_meta), \
         patch.object(client, "download_pdf", return_value=b"%PDF-1.4 mock bytes"), \
         patch.object(MarkdownParser, "parse_pdf", return_value=("# Mock Content " * 20, ["Intro"], [])):
        engine = PaperIngestionEngine(client=client)
        artifact = engine.ingest("1234.5678")

        assert artifact.paper_id == "1234.5678"
        assert artifact.extraction_source == PaperExtractionSource.PYMUPDF_MARKDOWN
        assert artifact.section_headers == ["Intro"]


def test_engine_tier2_html_fallback() -> None:
    client = ArxivClient()
    mock_meta = {
        "title": "Fallback Paper",
        "authors": ["Author B"],
        "published_date": "2024-01-01",
        "abstract": "Abstract",
        "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
    }
    mock_html = "<h1>HTML Title</h1><p>" + ("Fallback paragraph content. " * 10) + "</p>"

    with patch.object(client, "fetch_metadata", return_value=mock_meta), \
         patch.object(client, "download_pdf", side_effect=IngestionError("Download failed")), \
         patch.object(client, "fetch_ar5iv_html", return_value=mock_html):
        engine = PaperIngestionEngine(client=client)
        artifact = engine.ingest("1234.5678")

        assert artifact.paper_id == "1234.5678"
        assert artifact.extraction_source == PaperExtractionSource.ARXIV_HTML
        assert "HTML Title" in artifact.full_text_markdown


def test_engine_tier3_metadata_fallback() -> None:
    client = ArxivClient()
    mock_meta = {
        "title": "Metadata Paper",
        "authors": ["Author C"],
        "published_date": "2024-01-01",
        "abstract": "The sole abstract text.",
        "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
    }
    with patch.object(client, "fetch_metadata", return_value=mock_meta), \
         patch.object(client, "download_pdf", side_effect=IngestionError("PDF failed")), \
         patch.object(client, "fetch_ar5iv_html", return_value=None):
        engine = PaperIngestionEngine(client=client)
        artifact = engine.ingest("1234.5678")

        assert artifact.paper_id == "1234.5678"
        assert artifact.extraction_source == PaperExtractionSource.METADATA_FALLBACK
        assert "The sole abstract text." in artifact.full_text_markdown
