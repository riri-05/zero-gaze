"""Markdown parser and structural extractor using PyMuPDF4LLM."""

from __future__ import annotations

from html.parser import HTMLParser
import io
import re
from typing import Any
import pymupdf
import pymupdf4llm

from zero_gaze.core.errors import IngestionError
HEADER_PATTERN = re.compile(r"^\s*(#{1,4})\s+(.+)$", re.MULTILINE)
TABLE_ROW_PATTERN = re.compile(r"^\s*\|(.+)\|\s*$")


class _HTMLToMarkdownParser(HTMLParser):
    """Converts basic HTML elements to normalized markdown text."""

    def __init__(self) -> None:
        super().__init__()
        self._output = io.StringIO()
        self._in_script = False
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._in_script = True
        elif tag in ("h1", "h2", "h3", "h4"):
            level = int(tag[1])
            self._output.write(f"\n\n{'#' * level} ")
        elif tag in ("p", "div", "article", "section"):
            self._output.write("\n\n")
        elif tag == "li":
            self._output.write("\n- ")
        elif tag == "br":
            self._output.write("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._in_script = False
        elif tag in ("p", "div", "h1", "h2", "h3", "h4"):
            self._output.write("\n")

    def handle_data(self, data: str) -> None:
        if not self._in_script:
            self._output.write(data)

    def get_markdown(self) -> str:
        raw = self._output.getvalue()
        # Collapse multiple blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", raw)
        return cleaned.strip()


class MarkdownParser:
    """Extracts structured Markdown, headers, and tabular data from documents."""

    @classmethod
    def extract_headers(cls, markdown_text: str) -> list[str]:
        """Extract all Markdown heading titles in order of appearance."""
        headers: list[str] = []
        for match in HEADER_PATTERN.finditer(markdown_text):
            title = match.group(2).strip()
            # Exclude empty or punctuation-only headers
            if title and re.search(r"\w", title):
                headers.append(title)
        return headers

    @classmethod
    def extract_tables(cls, markdown_text: str) -> list[dict[str, Any]]:
        """Extract markdown tables into structured row dictionaries."""
        tables: list[dict[str, Any]] = []
        lines = markdown_text.splitlines()

        current_table_lines: list[str] = []

        def flush_table(raw_lines: list[str]) -> None:
            if len(raw_lines) < 3:
                return

            header_cells = [c.strip() for c in raw_lines[0].strip().strip("|").split("|")]
            # Line 1 is the separator: |---|---|
            separator_line = raw_lines[1]
            if not re.search(r"^[\|\s\-:]+$", separator_line):
                return

            rows: list[dict[str, str]] = []
            for row_line in raw_lines[2:]:
                cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
                row_dict = {}
                for idx, col_name in enumerate(header_cells):
                    val = cells[idx] if idx < len(cells) else ""
                    row_dict[col_name or f"col_{idx}"] = val
                rows.append(row_dict)

            if rows:
                tables.append({
                    "headers": header_cells,
                    "rows": rows,
                    "row_count": len(rows),
                })
        for line in lines:
            if TABLE_ROW_PATTERN.match(line):
                current_table_lines.append(line)
            else:
                if current_table_lines:
                    flush_table(current_table_lines)
                    current_table_lines = []

        if current_table_lines:
            flush_table(current_table_lines)

        return tables

    @classmethod
    def parse_pdf(
        cls,
        pdf_bytes: bytes,
        max_pages: int = 8,
    ) -> tuple[str, list[str], list[dict[str, Any]]]:
        """Convert PDF binary stream to structured Markdown using PyMuPDF4LLM."""
        if not pdf_bytes:
            raise IngestionError("Cannot parse empty PDF byte payload.")

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as err:
            raise IngestionError(
                f"PyMuPDF failed to open PDF stream: {err}",
                details={"error": str(err)},
            ) from err

        try:
            page_range = list(range(min(max_pages, len(doc))))
            markdown_content = pymupdf4llm.to_markdown(
                doc,
                pages=page_range,
                ignore_images=True,
                ignore_graphics=True,
            )
        except Exception as err:
            raise IngestionError(
                f"PyMuPDF4LLM failed to convert document to markdown: {err}",
                details={"error": str(err)},
            ) from err
        finally:
            doc.close()

        headers = cls.extract_headers(markdown_content)
        tables = cls.extract_tables(markdown_content)

        return markdown_content, headers, tables

    @classmethod
    def parse_html_to_markdown(cls, html_text: str) -> str:
        """Convert HTML text into clean Markdown."""
        parser = _HTMLToMarkdownParser()
        parser.feed(html_text)
        return parser.get_markdown()
