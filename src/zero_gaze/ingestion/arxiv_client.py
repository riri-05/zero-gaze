"""arXiv API client and network boundary gateway."""

from __future__ import annotations

import logging
import re
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from zero_gaze.core.errors import IngestionError

logger = logging.getLogger(__name__)

ARXIV_ID_PATTERN = re.compile(r"(?:arxiv\.org/(?:abs|pdf|html)/|arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)|([a-z\-]+(?:\.[a-z]{2})?/\d{7})", re.IGNORECASE)
USER_AGENT = "ZeroGaze/0.1.0 (+https://github.com/riri-05/zero-gaze)"


class ArxivClient:
    """Client gateway for interacting with arXiv API and fetching papers."""

    def __init__(
        self,
        base_query_url: str = "http://export.arxiv.org/api/query",
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> None:
        self.base_query_url = base_query_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @staticmethod
    def extract_arxiv_id(target: str) -> str:
        """Extract canonical arXiv ID from a URL, URN, or bare string.

        Examples:
            - '2106.09685' -> '2106.09685'
            - '2106.09685v2' -> '2106.09685v2'
            - 'arXiv:2106.09685' -> '2106.09685'
            - 'https://arxiv.org/abs/2106.09685' -> '2106.09685'
            - 'https://arxiv.org/pdf/2106.09685.pdf' -> '2106.09685'
        """
        cleaned = target.strip()
        match = ARXIV_ID_PATTERN.search(cleaned)
        if match:
            extracted = match.group(1) or match.group(2)
            if extracted:
                return extracted
        raise IngestionError(
            f"Could not parse valid arXiv ID from: '{target}'",
            details={"target": target},
        )

    def _make_request(self, url: str) -> bytes:
        """Execute HTTP request with exponential backoff and timeout."""
        headers = {"User-Agent": USER_AGENT}
        req = urllib.request.Request(url, headers=headers)

        last_error: Exception | None = None
        delay = 1.0

        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                    if response.status != 200:
                        raise IngestionError(
                            f"HTTP {response.status} fetching '{url}'",
                            details={"status_code": response.status, "url": url},
                        )
                    return response.read()
            except urllib.error.HTTPError as err:
                last_error = err
                if err.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    logger.warning("HTTP %d on attempt %d for %s. Retrying in %.1fs...", err.code, attempt, url, delay)
                    time.sleep(delay)
                    delay *= self.backoff_factor
                    continue
                raise IngestionError(
                    f"HTTP error {err.code} fetching arXiv resource: {err.reason}",
                    details={"status_code": err.code, "url": url},
                ) from err
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last_error = err
                if attempt < self.max_retries:
                    logger.warning("Network error on attempt %d for %s: %s. Retrying in %.1fs...", attempt, url, err, delay)
                    time.sleep(delay)
                    delay *= self.backoff_factor
                    continue
                raise IngestionError(
                    f"Network failure connecting to arXiv: {err}",
                    details={"url": url, "error": str(err)},
                ) from err

        raise IngestionError(
            f"Max retries exceeded fetching '{url}'",
            details={"url": url, "last_error": str(last_error)},
        )

    def fetch_metadata(self, arxiv_id: str) -> dict[str, Any]:
        """Fetch paper metadata from the arXiv Atom export API."""
        query_url = f"{self.base_query_url}?id_list={urllib.parse.quote(arxiv_id)}"
        xml_data = self._make_request(query_url)

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as err:
            raise IngestionError(
                f"Failed to parse arXiv Atom XML for '{arxiv_id}'",
                details={"arxiv_id": arxiv_id, "xml_data": xml_data[:200].decode("utf-8", errors="ignore")},
            ) from err

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            raise IngestionError(
                f"No entry found in arXiv for ID: '{arxiv_id}'",
                details={"arxiv_id": arxiv_id},
            )

        title_elem = entry.find("atom:title", ns)
        summary_elem = entry.find("atom:summary", ns)
        published_elem = entry.find("atom:published", ns)

        title = " ".join((title_elem.text or "").split()) if title_elem is not None else "Untitled"
        abstract = " ".join((summary_elem.text or "").split()) if summary_elem is not None else ""
        published_date = published_elem.text.strip() if published_elem is not None and published_elem.text else None

        authors: list[str] = []
        for author_elem in entry.findall("atom:author", ns):
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        return {
            "paper_id": arxiv_id,
            "title": title,
            "authors": authors,
            "published_date": published_date,
            "abstract": abstract,
            "pdf_url": pdf_url,
        }

    def download_pdf(self, pdf_url: str) -> bytes:
        """Download raw binary PDF bytes from the specified URL."""
        pdf_bytes = self._make_request(pdf_url)
        if not pdf_bytes.startswith(b"%PDF"):
            raise IngestionError(
                f"Downloaded bytes from '{pdf_url}' do not begin with valid PDF header.",
                details={"pdf_url": pdf_url, "header": pdf_bytes[:20]},
            )
        return pdf_bytes

    def fetch_ar5iv_html(self, arxiv_id: str) -> str | None:
        """Fallback to retrieve ar5iv HTML document if PDF parsing fails."""
        clean_id = arxiv_id.split("v")[0]
        url = f"https://ar5iv.labs.arxiv.org/html/{clean_id}"
        try:
            html_bytes = self._make_request(url)
            return html_bytes.decode("utf-8", errors="ignore")
        except IngestionError:
            logger.warning("ar5iv HTML fallback unavailable for %s", arxiv_id)
            return None
