"""Artifact discovery engine coordinating GitHub, Hugging Face, and synthetic stubs."""

from __future__ import annotations

import logging
from zero_gaze.core.models.discovery import CodeResource, RepoStatus
from zero_gaze.discovery.clients import (
    GitHubDiscoveryClient,
    HuggingFaceDiscoveryClient,
    PapersWithCodeClient,
)
from zero_gaze.discovery.synthetic_stub import SyntheticStubGenerator

logger = logging.getLogger(__name__)


class ArtifactDiscoveryEngine:
    """Discovers code repositories, benchmark datasets, and models with caching and stubbing."""

    def __init__(
        self,
        github_client: GitHubDiscoveryClient | None = None,
        hf_client: HuggingFaceDiscoveryClient | None = None,
        pwc_client: PapersWithCodeClient | None = None,
        stub_generator: type[SyntheticStubGenerator] = SyntheticStubGenerator,
    ) -> None:
        self.github_client = github_client or GitHubDiscoveryClient()
        self.hf_client = hf_client or HuggingFaceDiscoveryClient()
        self.pwc_client = pwc_client or PapersWithCodeClient()
        self.stub_generator = stub_generator
        self._cache: dict[str, CodeResource] = {}

    def discover(self, paper_id: str, paper_title: str) -> CodeResource:
        """Discover artifacts for a given paper or construct a synthetic baseline."""
        normalized_id = paper_id.strip().lower()
        if normalized_id in self._cache:
            logger.info("Returning cached CodeResource for paper: %s", paper_id)
            return self._cache[normalized_id]

        logger.info("Discovering artifacts for paper: %s ('%s')", paper_id, paper_title)

        # 1. Query Hugging Face Papers API
        hf_data = self.hf_client.query_paper(paper_id)
        linked_model_id = hf_data.get("primary_model") if hf_data else None
        linked_dataset_id = hf_data.get("primary_dataset") if hf_data else None
        dataset_url = f"https://huggingface.co/datasets/{linked_dataset_id}" if linked_dataset_id else None

        # 2. Query GitHub for matching implementations
        gh_repo = self.github_client.find_best_repository(paper_title=paper_title, arxiv_id=paper_id)

        # 3. If GitHub did not find a high-star repo, check PapersWithCode links
        if not gh_repo:
            pwc_repos = self.pwc_client.query_paper_repositories(paper_id)
            if pwc_repos:
                # Use the first repository from PapersWithCode
                pwc_url = pwc_repos[0]
                gh_repo = {
                    "repo_url": pwc_url,
                    "stars": 0,
                    "language": "python",
                    "license": None,
                }

        # 4. Determine status and construct CodeResource
        if gh_repo and gh_repo.get("repo_url"):
            stars = gh_repo.get("stars", 0)
            status = RepoStatus.OFFICIAL if stars >= 50 else RepoStatus.COMMUNITY

            resource = CodeResource(
                status=status,
                repo_url=gh_repo.get("repo_url"),
                commit_sha=gh_repo.get("commit_sha"),
                primary_language=gh_repo.get("language", "python"),
                entry_point_script="train.py",
                dataset_name=linked_dataset_id,
                dataset_download_url=dataset_url,
                huggingface_model_id=linked_model_id,
                stars=stars,
                license=gh_repo.get("license"),
                generated_baseline_code=None,
            )
        else:
            # Construct synthetic stub
            logger.info("No existing code found for %s. Generating synthetic stub.", paper_id)
            synthetic_code = self.stub_generator.generate_stub(
                paper_title=paper_title,
                arxiv_id=paper_id,
            )
            resource = CodeResource(
                status=RepoStatus.SYNTHETIC_STUB,
                repo_url=None,
                commit_sha=None,
                primary_language="python",
                entry_point_script="baseline_synthetic.py",
                dataset_name=linked_dataset_id or "synthetic_tensor_dataset",
                dataset_download_url=dataset_url,
                huggingface_model_id=linked_model_id,
                stars=0,
                license="MIT",
                generated_baseline_code=synthetic_code,
            )

        # Cache the result for idempotency
        self._cache[normalized_id] = resource
        return resource

    def clear_cache(self) -> None:
        """Clear discovery cache."""
        self._cache.clear()
