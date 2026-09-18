"""Context window protection and token budgeting for academic paper text."""

from __future__ import annotations

import re

BIBLIOGRAPHY_PATTERNS = [
    re.compile(r"^#{1,3}\s+(?:references|bibliography|works cited)\b.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\[\d+\]\s+[A-Z].+$", re.MULTILINE),
]


class TokenBudgeter:
    """Manages document truncation and focuses on high-signal empirical sections."""

    @classmethod
    def strip_bibliography(cls, markdown_text: str) -> str:
        """Strip trailing reference and bibliography sections."""
        for pattern in BIBLIOGRAPHY_PATTERNS:
            match = pattern.search(markdown_text)
            if match and match.start() > 500:
                # Truncate at the start of the bibliography
                return markdown_text[: match.start()].strip()
        return markdown_text

    @classmethod
    def budget_paper_text(
        cls,
        full_text: str,
        max_characters: int = 32000,
    ) -> str:
        """Truncate paper text to stay within model prompt budgets while preserving core sections."""
        clean_text = cls.strip_bibliography(full_text)
        if len(clean_text) <= max_characters:
            return clean_text

        # If text exceeds budget, slice at paragraph break
        truncated = clean_text[:max_characters]
        last_double_newline = truncated.rfind("\n\n")
        if last_double_newline > max_characters * 0.7:
            truncated = truncated[:last_double_newline]

        return (
            truncated
            + "\n\n[... Note: Subsequent paper appendix sections truncated to fit model context budget ...]"
        )
