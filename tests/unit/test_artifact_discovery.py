"""Unit tests for artifact discovery engine and clients."""

from unittest.mock import MagicMock, patch
import pytest
from zero_gaze.core.models.discovery import RepoStatus
from zero_gaze.discovery.clients import (
    GitHubDiscoveryClient,
    HuggingFaceDiscoveryClient,
    PapersWithCodeClient,
)
from zero_gaze.discovery.engine import ArtifactDiscoveryEngine
from zero_gaze.discovery.synthetic_stub import SyntheticStubGenerator


def test_huggingface_client_parses_linked_assets() -> None:
    mock_hf_json = {
        "title": "Sample Paper",
        "upvotes": 42,
        "linkedModels": [{"id": "org/model-v1"}, {"id": "org/model-v2"}],
        "linkedDatasets": [{"id": "org/benchmark-data"}],
    }
    client = HuggingFaceDiscoveryClient()
    with patch.object(client.http_client, "get_json", return_value=mock_hf_json):
        result = client.query_paper("2106.09685")
        assert result is not None
        assert result["title"] == "Sample Paper"
        assert result["primary_model"] == "org/model-v1"
        assert result["primary_dataset"] == "org/benchmark-data"
        assert result["upvotes"] == 42


def test_huggingface_client_handles_none_response() -> None:
    client = HuggingFaceDiscoveryClient()
    with patch.object(client.http_client, "get_json", return_value=None):
        result = client.query_paper("invalid-id")
        assert result is None


def test_github_client_search_repositories() -> None:
    mock_gh_json = {
        "items": [
            {
                "html_url": "https://github.com/microsoft/LoRA",
                "full_name": "microsoft/LoRA",
                "stargazers_count": 13800,
                "language": "Python",
                "license": {"spdx_id": "MIT"},
            }
        ]
    }
    client = GitHubDiscoveryClient()
    with patch.object(client.http_client, "get_json", return_value=mock_gh_json):
        results = client.search_repositories("LoRA")
        assert len(results) == 1
        assert results[0]["repo_url"] == "https://github.com/microsoft/LoRA"
        assert results[0]["stars"] == 13800
        assert results[0]["license"] == "MIT"
        assert results[0]["language"] == "python"


def test_github_client_find_best_repository_by_arxiv_id() -> None:
    mock_gh_json = {
        "items": [
            {
                "html_url": "https://github.com/user/exact-paper",
                "full_name": "user/exact-paper",
                "stargazers_count": 25,
                "language": "Python",
                "license": None,
            }
        ]
    }
    client = GitHubDiscoveryClient()
    with patch.object(client.http_client, "get_json", return_value=mock_gh_json):
        best = client.find_best_repository(paper_title="Some Title", arxiv_id="2106.09685")
        assert best is not None
        assert best["repo_url"] == "https://github.com/user/exact-paper"


def test_paperswithcode_client_parses_repositories() -> None:
    mock_paper_json = {"count": 1, "results": [{"id": "lora-paper-id"}]}
    mock_repo_json = {"results": [{"url": "https://github.com/microsoft/LoRA"}]}

    client = PapersWithCodeClient()

    def mock_get(url: str, **kwargs):
        if "repositories" in url:
            return mock_repo_json
        return mock_paper_json

    with patch.object(client.http_client, "get_json", side_effect=mock_get):
        repos = client.query_paper_repositories("2106.09685")
        assert repos == ["https://github.com/microsoft/LoRA"]


def test_synthetic_stub_generator_output() -> None:
    code = SyntheticStubGenerator.generate_stub(
        paper_title="Attention Is All You Need",
        arxiv_id="1706.03762",
        target_metric="BLEU",
        epochs=3,
    )
    assert "Attention Is All You Need" in code
    assert "1706.03762" in code
    assert "class SyntheticBaselineModel" in code
    assert "def run_experiment()" in code
    assert "torch" in code


def test_discovery_engine_returns_official_repo() -> None:
    engine = ArtifactDiscoveryEngine()
    mock_hf = {"primary_model": "test-org/model", "primary_dataset": "test-org/dataset"}
    mock_gh = {
        "repo_url": "https://github.com/test-org/official-repo",
        "stars": 600,
        "language": "python",
        "license": "Apache-2.0",
        "commit_sha": "abc1234",
    }

    with patch.object(engine.hf_client, "query_paper", return_value=mock_hf), \
         patch.object(engine.github_client, "find_best_repository", return_value=mock_gh):
        resource = engine.discover("2106.09685", "LoRA")

        assert resource.status == RepoStatus.OFFICIAL
        assert resource.repo_url == "https://github.com/test-org/official-repo"
        assert resource.stars == 600
        assert resource.huggingface_model_id == "test-org/model"
        assert resource.dataset_name == "test-org/dataset"
        assert resource.generated_baseline_code is None


def test_discovery_engine_returns_community_repo() -> None:
    engine = ArtifactDiscoveryEngine()
    mock_gh = {
        "repo_url": "https://github.com/student/community-reproduction",
        "stars": 15,
        "language": "python",
        "license": "MIT",
    }

    with patch.object(engine.hf_client, "query_paper", return_value=None), \
         patch.object(engine.github_client, "find_best_repository", return_value=mock_gh):
        resource = engine.discover("1234.5678", "Paper Title")

        assert resource.status == RepoStatus.COMMUNITY
        assert resource.stars == 15


def test_discovery_engine_falls_back_to_synthetic_stub() -> None:
    engine = ArtifactDiscoveryEngine()

    with patch.object(engine.hf_client, "query_paper", return_value=None), \
         patch.object(engine.github_client, "find_best_repository", return_value=None), \
         patch.object(engine.pwc_client, "query_paper_repositories", return_value=[]):
        resource = engine.discover("0000.0000", "Unknown Method")

        assert resource.status == RepoStatus.SYNTHETIC_STUB
        assert resource.repo_url is None
        assert resource.generated_baseline_code is not None
        assert "SyntheticBaselineModel" in resource.generated_baseline_code


def test_discovery_engine_idempotent_caching() -> None:
    engine = ArtifactDiscoveryEngine()
    mock_gh = {"repo_url": "https://github.com/repo/one", "stars": 100}

    with patch.object(engine.hf_client, "query_paper", return_value=None), \
         patch.object(engine.github_client, "find_best_repository", return_value=mock_gh) as mock_find:
        res1 = engine.discover("2106.09685", "LoRA")
        res2 = engine.discover("2106.09685", "LoRA")

        assert res1 is res2
        # GitHub search should only have been called once
        assert mock_find.call_count == 1


def test_discovery_engine_clear_cache() -> None:
    engine = ArtifactDiscoveryEngine()
    mock_gh = {"repo_url": "https://github.com/repo/one", "stars": 100}

    with patch.object(engine.hf_client, "query_paper", return_value=None), \
         patch.object(engine.github_client, "find_best_repository", return_value=mock_gh) as mock_find:
        engine.discover("2106.09685", "LoRA")
        engine.clear_cache()
        engine.discover("2106.09685", "LoRA")

        assert mock_find.call_count == 2
