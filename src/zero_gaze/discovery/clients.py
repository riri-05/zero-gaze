"""Discovery clients for Hugging Face, GitHub, and PapersWithCode."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "ZeroGaze/0.1.0 (+https://github.com/riri-05/zero-gaze)",
    "Accept": "application/json",
}


class DiscoveryHttpClient:
    """Base HTTP client with timeout and exception shielding."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_json(self, url: str, extra_headers: dict[str, str] | None = None) -> Any:
        headers = dict(DEFAULT_HEADERS)
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    # In case endpoint returned HTML or unexpected type
                    raw = resp.read().decode("utf-8", errors="ignore")
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        return None
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as err:
            logger.warning("HTTP %d error accessing %s: %s", err.code, url, err.reason)
            return None
        except Exception as err:
            logger.warning("Network failure accessing %s: %s", url, err)
            return None


class HuggingFaceDiscoveryClient:
    """Client for Hugging Face Papers API."""

    def __init__(self, http_client: DiscoveryHttpClient | None = None) -> None:
        self.http_client = http_client or DiscoveryHttpClient()

    def query_paper(self, arxiv_id: str) -> dict[str, Any] | None:
        """Query Hugging Face Daily Papers API for linked models and datasets."""
        clean_id = arxiv_id.split("v")[0]
        url = f"https://huggingface.co/api/papers/{clean_id}"
        data = self.http_client.get_json(url)
        if not isinstance(data, dict):
            return None

        linked_models = [
            m.get("id") for m in data.get("linkedModels", []) if isinstance(m, dict) and m.get("id")
        ]
        linked_datasets = [
            d.get("id") for d in data.get("linkedDatasets", []) if isinstance(d, dict) and d.get("id")
        ]

        return {
            "title": data.get("title"),
            "upvotes": data.get("upvotes", 0),
            "linked_models": linked_models,
            "linked_datasets": linked_datasets,
            "primary_model": linked_models[0] if linked_models else None,
            "primary_dataset": linked_datasets[0] if linked_datasets else None,
        }


class GitHubDiscoveryClient:
    """Client for GitHub Search REST API."""

    def __init__(self, http_client: DiscoveryHttpClient | None = None) -> None:
        self.http_client = http_client or DiscoveryHttpClient()

    @staticmethod
    def _sanitize_query(title: str) -> str:
        """Clean paper title for search query construction."""
        # Remove LaTeX and non-alphanumeric punctuation
        clean = re.sub(r"[\$\\\{\}\:\;\,\.\?\!\(\)\[\]]", " ", title)
        words = clean.split()
        # Keep up to 6 significant words
        significant = [w for w in words if len(w) > 2 and w.lower() not in ("the", "and", "for", "with")][:6]
        return " ".join(significant)

    def search_repositories(self, query: str, sort: str = "stars") -> list[dict[str, Any]]:
        """Search GitHub repositories by query string sorted by stars."""
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded_query}&sort={sort}&order=desc&per_page=5"
        headers = {"Accept": "application/vnd.github+json"}
        data = self.http_client.get_json(url, extra_headers=headers)
        if not isinstance(data, dict) or "items" not in data:
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            license_info = item.get("license")
            license_name = license_info.get("spdx_id") if isinstance(license_info, dict) else None

            results.append({
                "repo_url": item.get("html_url"),
                "full_name": item.get("full_name"),
                "description": item.get("description"),
                "stars": item.get("stargazers_count", 0),
                "language": (item.get("language") or "python").lower(),
                "default_branch": item.get("default_branch", "main"),
                "license": license_name,
            })
        return results

    def find_best_repository(self, paper_title: str, arxiv_id: str) -> dict[str, Any] | None:
        """Find the most relevant open-source repository for a paper."""
        # Strategy 1: Search by exact arXiv identifier
        arxiv_results = self.search_repositories(arxiv_id)
        if arxiv_results and arxiv_results[0]["stars"] >= 10:
            return arxiv_results[0]

        # Strategy 2: Search by title keywords
        keyword_query = self._sanitize_query(paper_title)
        if keyword_query:
            title_results = self.search_repositories(keyword_query)
            if title_results:
                # Return highest starred matching repository
                return title_results[0]

        return None


class PapersWithCodeClient:
    """Client for PapersWithCode REST API."""

    def __init__(self, http_client: DiscoveryHttpClient | None = None) -> None:
        self.http_client = http_client or DiscoveryHttpClient()

    def query_paper_repositories(self, arxiv_id: str) -> list[str]:
        """Query PapersWithCode for repository URLs associated with arXiv ID."""
        clean_id = arxiv_id.split("v")[0]
        url = f"https://paperswithcode.com/api/v1/papers/?arxiv_id={clean_id}"
        data = self.http_client.get_json(url)
        if not isinstance(data, dict) or data.get("count", 0) == 0:
            return []

        results = data.get("results", [])
        if not results or not isinstance(results[0], dict):
            return []

        paper_id = results[0].get("id")
        if not paper_id:
            return []

        code_url = f"https://paperswithcode.com/api/v1/papers/{paper_id}/repositories/"
        code_data = self.http_client.get_json(code_url)
        if not isinstance(code_data, dict):
            return []

        repos = []
        for r in code_data.get("results", []):
            if isinstance(r, dict) and r.get("url"):
                repos.append(r["url"])
        return repos
